import pygame
import os

_SOUNDS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "music"
)

class SoundManager:
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._load_all()

    # ── Load ──────────────────────────────────────────────────────────────────
    def _load(self, key: str, filename: str, volume: float = 1.0):
        path = os.path.join(_SOUNDS_DIR, filename)
        if os.path.exists(path):
            snd = pygame.mixer.Sound(path)
            snd.set_volume(volume)
            self._sfx[key] = snd

    def _load_all(self):
        self._load("btn_click",  "sound_button.mp3",  volume=1)
        self._load("place_x",    "sound_tick.wav",    volume=1.0)
        self._load("place_o",    "sound_tick.wav",    volume=1.0)
        
        print("Loaded keys:", list(self._sfx.keys()))

    # ── BGM ───────────────────────────────────────────────────────────────────
    def play_bgm(self, filename: str = "sound_background.mp3", volume: float = 1):
        path = os.path.join(_SOUNDS_DIR, filename)
        if not os.path.exists(path):
            return
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(loops=-1)   # -1 = loop mãi

    def stop_bgm(self):
        pygame.mixer.music.stop()

    def pause_bgm(self):
        pygame.mixer.music.pause()

    def resume_bgm(self):
        pygame.mixer.music.unpause()

    # ── SFX ───────────────────────────────────────────────────────────────────
    def play(self, key: str):
        snd = self._sfx.get(key)
        if snd:
            snd.play()