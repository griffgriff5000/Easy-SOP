"""Record only an owned test window, then verify synthetic narration export."""
from pathlib import Path
import sys,time,math,struct,subprocess,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sop_capture.video_recorder import VideoRecorder,configure_media_runtime
configure_media_runtime()
from PySide6.QtWidgets import QApplication,QLabel
from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QWindowCapture
from sop_capture.training_video import VideoSession
from sop_capture.media_export import VideoExport,ffmpeg_executable


def main():
    app=QApplication([]);app.setQuitOnLastWindowClosed(False)
    root=Path('.superpowers/video-check').resolve();root.mkdir(parents=True,exist_ok=True)
    video=VideoSession.create(root,'Synthetic window capture')
    window=QLabel('SOP VIDEO TEST — synthetic content only');window.setWindowTitle('SOP video verification '+video.root.name)
    window.setStyleSheet('background:#0c8291;color:white;font-size:22px;padding:30px;');window.resize(640,360);window.show();app.processEvents()
    sources=[w for w in QWindowCapture.capturableWindows() if w.description()==window.windowTitle()]
    assert sources,'Owned synthetic window was not capturable'
    recorder=VideoRecorder();results=[];errors=[];stop=QTimer();stop.setSingleShot(True);stop.timeout.connect(recorder.stop)
    recorder.changed.connect(lambda state:stop.start(3000) if state=='recording' and not stop.isActive() else None)
    recorder.completed.connect(lambda *args:(results.append(args),app.quit()))
    recorder.error.connect(errors.append)
    watchdog=QTimer();watchdog.setSingleShot(True);watchdog.timeout.connect(lambda:(recorder.stop(),app.quit()));watchdog.start(20000)
    ticks=QTimer();ticks.timeout.connect(lambda:window.setText('Synthetic training window\n'+str(round(time.monotonic(),1))));ticks.start(200)
    recorder.start_video(('window',sources[0]),None,video.new_asset('recording','.mkv'));app.exec();watchdog.stop();ticks.stop();stop.stop()
    assert results and not errors,(results,errors)
    mode,path,duration,error=results[0];assert not error and duration>=1500,(duration,error)
    video.original=path.name;video.duration=duration/1000
    narration=video.new_asset('synthetic-voice','.wav')
    samples=b''.join(struct.pack('<h',int(12000*math.sin(2*math.pi*440*n/48000))) for n in range(48000))
    narration.write_bytes(struct.pack('<4sI4s4sIHHIIHH4sI',b'RIFF',36+len(samples),b'WAVE',b'fmt ',16,1,1,48000,96000,2,16,b'data',len(samples))+samples)
    video.narration=narration.name;video.use_narration=True;video.trim_start=.25;video.trim_end=min(2.5,video.duration);video.volume=.5;video.save()
    output=video.root/'export.mp4';export=VideoExport();exported=[]
    export.finished.connect(lambda path,error:(exported.append((path,error)),app.quit()));watchdog.start(30000)
    export.start(video,output);app.exec();watchdog.stop()
    assert exported and exported[0][1] is None,exported
    decoded=subprocess.run([ffmpeg_executable(),'-v','error','-i',str(output),'-map','0:a:0','-f','s16le','-ac','1','-ar','48000','pipe:1'],capture_output=True,check=True)
    audio_seconds=len(decoded.stdout)/2/48000
    assert abs(audio_seconds-(video.trim_end-video.trim_start))<.15,audio_seconds
    peak=max(abs(x[0]) for x in struct.iter_unpack('<h',decoded.stdout[:40000]))
    assert 4000<peak<8000,peak
    assert max(abs(x[0]) for x in struct.iter_unpack('<h',decoded.stdout[-9600:]))<100
    assert path.is_file() and narration.is_file()
    video.use_narration=False;exported.clear();export.start(video,video.root/'silent-export.mp4');watchdog.start(30000);app.exec();watchdog.stop()
    assert exported and exported[0][1] is None,exported
    print('Owned window recording, trimmed MP4 and padded synthetic narration passed:',video.root,flush=True)
    window.close();recorder.deleteLater();app.processEvents()


if __name__=='__main__':main()
