"""Exercise section export using synthetic media only; no microphone or screen capture."""
from pathlib import Path
import sys,subprocess,time,re,struct
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sop_capture.video_recorder import configure_media_runtime
configure_media_runtime()
from PySide6.QtWidgets import QApplication
from sop_capture.training_video import VideoSession
from sop_capture.video_timeline import legacy_section
from sop_capture.media_export import VideoExport,ffmpeg_executable


def main():
    app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
    from sop_capture.ui.theme import stylesheet
    app.setStyleSheet(stylesheet(False))
    root=Path('.superpowers/video-editor-check').resolve();session=VideoSession.create(root,'Synthetic edit')
    executable=ffmpeg_executable()
    for name,size,colour,audio in [('silent.mp4','640x480','blue',False),('sound.mp4','960x540','green',True)]:
        args=[executable,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'color=c={colour}:s={size}:r=30']
        if audio:args+=['-f','lavfi','-i','sine=frequency=440:sample_rate=48000']
        subprocess.run(args+['-t','2','-c:v','libx264','-pix_fmt','yuv420p',str(session.asset(name))],check=True,capture_output=True)
    session.original='silent.mp4';session.duration=2
    first=legacy_section(session);first.update(start=.25,end=1.25)
    first['overlays']=[dict(start=.2,end=.8,annotation=dict(kind='highlighter',points=[100,100,300,300],color='#ff0000',opacity=100))]
    subprocess.run([executable,'-v','error','-y','-f','lavfi','-i','sine=frequency=880:sample_rate=48000','-t','1',str(session.asset('voice.wav'))],capture_output=True,check=True)
    second=legacy_section(session);second.update(source='sound.mp4',start=.5,end=1.5,narration='voice.wav',narration_origin=.75,use_narration=True,volume=.5)
    title=dict(kind='card',title='TRAINING',text='Synthetic title',duration=.5,background='#123456',foreground='#ffffff',logo=None,overlays=[])
    credits=title|dict(title='CREDITS',text='Synthetic credits',background='#654321')
    session.timeline=[title,first,second,credits];session.save();original=session.asset('silent.mp4').read_bytes()
    job=VideoExport();results=[];job.finished.connect(lambda path,error:results.append((path,error)))
    output=session.root/'edited.mp4';job.start(session,output);deadline=time.monotonic()+60
    while not results and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert results and results[0][1] is None,results
    def frame(position):
        result=subprocess.run([executable,'-v','error','-ss',str(position),'-i',str(output),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True)
        assert len(result.stdout)==1280*720*3
        return result.stdout
    def pixel(data,x,y):return data[(y*1280+x)*3:(y*1280+x)*3+3]
    assert max(abs(a-b) for a,b in zip(pixel(frame(.1),10,10),(18,52,86)))<8
    before=pixel(frame(.6),200,200);during=pixel(frame(1),200,200);after=pixel(frame(1.4),200,200)
    assert before[2]>200 and during[0]>200 and during[2]<30 and after[2]>200,(before,during,after)
    assert max(abs(a-b) for a,b in zip(pixel(frame(2.8),10,10),(101,67,33)))<8
    audio=subprocess.run([executable,'-v','error','-i',str(output),'-map','0:a','-f','s16le','-ac','1','-ar','48000','pipe:1'],capture_output=True,check=True).stdout
    assert abs(len(audio)/96000-3)<.15,len(audio)/96000
    def peak(start,end):return max(abs(x[0]) for x in struct.iter_unpack('<h',audio[round(start*48000)*2:round(end*48000)*2]))
    assert peak(1.58,1.65)<100,'Narration should be delayed relative to the trimmed source'
    assert 1000<peak(2,2.1)<3000,'Section narration should use the selected half-volume'
    assert session.asset('silent.mp4').read_bytes()==original
    # Native editor preview and import are exercised without opening any microphone.
    from sop_capture.ui.video_editor import VideoEditorDialog
    editor=VideoEditorDialog(session);editor.show();editor.sections.setCurrentRow(1)
    deadline=time.monotonic()+5
    while not editor.player.hasVideo() and time.monotonic()<deadline:app.processEvents();time.sleep(.02)
    assert editor.player.hasVideo();editor.seek(500);editor.play_pause()
    until=time.monotonic()+.5
    while time.monotonic()<until:app.processEvents();time.sleep(.01)
    editor.pause_playback()
    # Exercise the real asynchronous import/probe pipeline, with a local synthetic file.
    from PySide6.QtWidgets import QFileDialog
    original_dialog=QFileDialog.getOpenFileName
    QFileDialog.getOpenFileName=lambda *a,**k:(str(session.asset('sound.mp4')),'')
    try:editor.import_clip()
    finally:QFileDialog.getOpenFileName=original_dialog
    deadline=time.monotonic()+15
    while editor.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert not editor.busy and len(editor.session.timeline)==5,editor.status.text()
    editor.sections.setCurrentRow(0)
    app.processEvents();editor.grab().save(str(root/'editor.png'))
    for attempt in range(4):
        editor.export(True);deadline=time.monotonic()+60
        while editor.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert not editor.busy and editor.previewing,editor.status.text()
        until=time.monotonic()+.3
        while time.monotonic()<until:app.processEvents();time.sleep(.01)
        editor.pause_playback();editor.seek(3500);assert editor.relative_position==3.5
    editor.close();print('Synthetic sequence: cards, silent/mixed clips, timed overlay, audio duration, native editor playback passed:',output)

if __name__=='__main__':main()
