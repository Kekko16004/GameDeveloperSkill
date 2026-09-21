using System.Collections.Generic;
using UnityEngine;

namespace Game.Audio
{
    public class AudioManager : MonoBehaviour
    {
        public static AudioManager Instance { get; private set; }

        [Header("Audio Sources")]
        [SerializeField] private AudioSource musicSource;
        [SerializeField] private AudioSource ambienceSource;
        [SerializeField] private AudioSource uiSource;
        [SerializeField] private int sfxPoolSize = 8;

        [Header("Audio Clips Library")]
        [SerializeField] private List<NamedAudioClip> sfxClips = new List<NamedAudioClip>();
        [SerializeField] private List<NamedAudioClip> footstepClips = new List<NamedAudioClip>();

        private readonly List<AudioSource> sfxPool = new List<AudioSource>();
        private readonly Dictionary<string, AudioClip> sfxDict = new Dictionary<string, AudioClip>();
        private readonly Dictionary<string, List<AudioClip>> footstepDict = new Dictionary<string, List<AudioClip>>();

        [System.Serializable]
        public struct NamedAudioClip
        {
            public string name;
            public AudioClip clip;
        }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);

            InitializeSources();
            BuildDictionaries();
        }

        private void InitializeSources()
        {
            if (musicSource == null)
            {
                musicSource = gameObject.AddComponent<AudioSource>();
                musicSource.loop = true;
                musicSource.playOnAwake = false;
            }

            if (ambienceSource == null)
            {
                ambienceSource = gameObject.AddComponent<AudioSource>();
                ambienceSource.loop = true;
                ambienceSource.playOnAwake = false;
            }

            if (uiSource == null)
            {
                uiSource = gameObject.AddComponent<AudioSource>();
                uiSource.loop = false;
                uiSource.playOnAwake = false;
            }

            for (int i = 0; i < sfxPoolSize; i++)
            {
                AudioSource src = gameObject.AddComponent<AudioSource>();
                src.loop = false;
                src.playOnAwake = false;
                sfxPool.Add(src);
            }
        }

        private void BuildDictionaries()
        {
            foreach (var item in sfxClips)
            {
                if (!string.IsNullOrEmpty(item.name) && item.clip != null)
                {
                    sfxDict[item.name.ToLower()] = item.clip;
                }
            }

            foreach (var item in footstepClips)
            {
                if (!string.IsNullOrEmpty(item.name) && item.clip != null)
                {
                    string key = item.name.ToLower();
                    if (!footstepDict.ContainsKey(key))
                    {
                        footstepDict[key] = new List<AudioClip>();
                    }
                    footstepDict[key].Add(item.clip);
                }
            }
        }

        public void PlaySFX(AudioClip clip, float volume = 1f, float pitch = 1f)
        {
            if (clip == null) return;
            AudioSource source = GetAvailableSFXSource();
            source.pitch = pitch;
            source.PlayOneShot(clip, volume);
        }

        public void PlaySFX(string soundName, float volume = 1f)
        {
            if (string.IsNullOrEmpty(soundName)) return;
            string key = soundName.ToLower();
            if (sfxDict.TryGetValue(key, out AudioClip clip))
            {
                PlaySFX(clip, volume);
            }
        }

        public void PlayFootstep(string surfaceType = "stone", float volume = 0.6f)
        {
            string key = surfaceType.ToLower();
            if (footstepDict.TryGetValue(key, out List<AudioClip> clips) && clips.Count > 0)
            {
                AudioClip randomClip = clips[Random.Range(0, clips.Count)];
                float randomPitch = Random.Range(0.92f, 1.08f);
                PlaySFX(randomClip, volume, randomPitch);
            }
        }

        public void PlayUI(AudioClip clip, float volume = 1f)
        {
            if (clip == null || uiSource == null) return;
            uiSource.PlayOneShot(clip, volume);
        }

        public void PlayMusic(AudioClip clip, float volume = 0.7f)
        {
            if (clip == null || musicSource == null) return;
            musicSource.clip = clip;
            musicSource.volume = volume;
            musicSource.Play();
        }

        public void PlayAmbience(AudioClip clip, float volume = 0.5f)
        {
            if (clip == null || ambienceSource == null) return;
            ambienceSource.clip = clip;
            ambienceSource.volume = volume;
            ambienceSource.Play();
        }

        public void StopMusic()
        {
            if (musicSource != null) musicSource.Stop();
        }

        public void StopAmbience()
        {
            if (ambienceSource != null) ambienceSource.Stop();
        }

        private AudioSource GetAvailableSFXSource()
        {
            foreach (var src in sfxPool)
            {
                if (!src.isPlaying) return src;
            }
            return sfxPool[0];
        }
    }
}
