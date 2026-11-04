"""Generate real local speech, apply it through the video editor and verify the exported MP4 audio (synthetic video only; no microphone)."""
from pathlib import Path
import sys,subprocess,time,struct,math,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sop_capture.video_recorder import configure_media_runtime
configure_media_runtime()
from PySide6.QtWidgets import QApplication
from sop_capture import speech_runtime as speech
from sop_capture.training_video import VideoSession
from sop_capture.media_export import VideoExport,ffmpeg_executable
from sop_capture.ui.video_editor import VideoEditorDialog


def ensure_runtime():
    target=speech.runtime_path()
    if speech.verify_runtime(target):return target
    source=Path('.superpowers/tts-inspect')
    opener=lambda request,timeout=0:(source/('engine.tar.bz2' if '/v2.0.1/' in request.full_url else 'model.tar.bz2')).open('rb')
    return speech.install_runtime(opener=opener) if source.is_dir() else speech.install_runtime()


def windows(executable,path,step=.5):
    raw=subprocess.run([executable,'-v','error','-i',str(path),'-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'],capture_output=True,check=True).stdout
    samples=struct.unpack(f'<{len(raw)//2}h',raw);size=int(16000*step)
    return len(samples)/16000,[math.sqrt(sum(s*s for s in samples[i:i+size])/max(1,len(samples[i:i+size]))) for i in range(0,len(samples),size)]


def main():
    app=QApplication.instance() or QApplication([]);executable=ffmpeg_executable();target=ensure_runtime()
    root=Path(tempfile.mkdtemp(prefix='sop-speech-verify-'));session=VideoSession.create(root,'Speech check')
    subprocess.run([executable,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=blue:s=640x480:r=30','-t','4','-c:v','libx264','-pix_fmt','yuv420p',str(session.asset('silent.mp4'))],check=True)
    session.original='silent.mp4';session.duration=4;session.save()
    editor=VideoEditorDialog(session);results={}
    for label,text,voice in [('long','Open the permit register, select the active permit, and review the isolation details before you continue with the work.',24),('short','Open the register.',21)]:
        wav=root/f'{label}-source.wav';duration=speech.synthesize(text,voice,1,wav,target=target)
        editor._apply_speech(0,wav,dict(script=text,voice=voice,speed=1.0))
        item=editor.current();assert item['speech']['voice']==voice and item['narration_origin']==item['start'] and item['use_narration']
        reopened=VideoSession.load(session.root);assert reopened.timeline[0]['speech']==item['speech']
        output=root/f'{label}.mp4';job=VideoExport();done=[];job.finished.connect(lambda path,error:done.append((path,error)))
        job.start(editor.session,output);deadline=time.monotonic()+90
        while not done and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert done and done[0][1] is None,done
        length,levels=windows(executable,output);results[label]=(duration,length,levels)
        print(label,'narration',round(duration,2),'s; exported audio',round(length,2),'s; levels',[round(v) for v in levels])
    assert abs(results['long'][1]-4)<.3 and results['long'][0]>4 and results['long'][2][-2]>100,'long narration should be trimmed, not shortened video'
    assert abs(results['short'][1]-4)<.3 and results['short'][2][0]>100 and results['short'][2][-1]<50,'short narration should start at section start then pad silence'
    assert len(list(session.root.glob('section-voiceover-*.wav')))==2
    print('ok')
    editor.close()


if __name__=='__main__':main()
