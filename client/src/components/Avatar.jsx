import { useRef, useState, useEffect } from "react";
import femaleVideo from "./../assets/female.mp4";
import audio from "./../assets/audio.mp3";

const Avatar = () => {
  const videoRef = useRef(null);
  const audioRef = useRef(null);
  const [isMediaPlaying, setIsMediaPlaying] = useState(false);

  useEffect(() => {
    const videoElement = videoRef.current;
    const audioElement = audioRef.current;

    const playMedia = async () => {
      if (videoElement && audioElement) {
        videoElement.muted = true;
        try {
          await videoElement.play();
          await audioElement.play();
          setIsMediaPlaying(true);
        } catch (err) {
          console.error("Autoplay failed, waiting for user interaction", err);
        }
      }
    };

    playMedia();

    return () => {
      if (videoElement) videoElement.pause();
      if (audioElement) audioElement.pause();
    };
  }, []);

  const handleUserInteraction = () => {
    if (videoRef.current && audioRef.current) {
      videoRef.current.muted = true;
      videoRef.current.play();
      audioRef.current.play();
      setIsMediaPlaying(true);
    }
  };

  return (
    <div
      className="avatar-overlay"
      style={{
        position: "fixed",
        bottom: "10px",
        right: "10px",
        width: "250px",
        height: "250px",
        zIndex: 10,
      }}
    >
      <div
        className="avatar"
        style={{
          width: "100%",
          height: "100%",
          borderRadius: "50%",
          backgroundColor: "transparent",
          border: "none",
        }}
      >
        <video
          ref={videoRef}
          loop={false}
          playsInline
          preload="auto"
          autoPlay
          style={{
            width: "100%",
            height: "100%",
            borderRadius: "50%",
            backgroundColor: "transparent",
          }}
        >
          <source src={femaleVideo} type="video/mp4" />
          <source src={femaleVideo} type="video/webm" />
          <p>Your browser does not support HTML5 video.</p>
        </video>
        <audio
          ref={audioRef}
          src={audio}
          controls
          preload="auto"
          autoPlay
          muted={false}
        />
      </div>

      {!isMediaPlaying && (
        <button
          onClick={handleUserInteraction}
          style={{
            position: "absolute",
            top: "10px",
            left: "10px",
            zIndex: 20,
          }}
        >
          Play Video and Audio
        </button>
      )}
    </div>
  );
};

export default Avatar;
