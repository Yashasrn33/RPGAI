/*
 * TTS Audio Player
 * Fetches synthesized audio from the backend and plays it in Unity.
 */

using UnityEngine;
using UnityEngine.Networking;
using System.Threading.Tasks;
using RPGAI.Net;

namespace RPGAI.Audio
{
    [System.Serializable]
    public class TTSRequest
    {
        public string ssml;
        public string voice_name = "en-US-Neural2-C";
    }

    [System.Serializable]
    public class TTSResponse
    {
        public string audio_url;
    }

    [RequireComponent(typeof(AudioSource))]
    public class TTSPlayer : MonoBehaviour
    {
        [Header("Backend Configuration")]
        [SerializeField] private string ttsEndpoint = "http://localhost:8000/v1/voice/tts";

        private AudioSource audioSource;

        private void Awake()
        {
            audioSource = GetComponent<AudioSource>();
        }

        /// <summary>
        /// Request TTS synthesis and play the audio.
        /// </summary>
        /// <param name="text">Plain text utterance</param>
        /// <param name="voiceName">Google Cloud voice name</param>
        public async Task PlayTTS(string text, string voiceName = "en-US-Neural2-C")
        {
            // Wrap text in basic SSML
            string ssml = $"<speak>{text}</speak>";
            await PlayTTSFromSSML(ssml, voiceName);
        }

        /// <summary>
        /// Request TTS synthesis from SSML and play the audio.
        /// </summary>
        /// <param name="ssml">SSML-formatted text</param>
        /// <param name="voiceName">Google Cloud voice name</param>
        public async Task PlayTTSFromSSML(string ssml, string voiceName = "en-US-Neural2-C")
        {
            try
            {
                // Request synthesis
                var request = new TTSRequest
                {
                    ssml = ssml,
                    voice_name = voiceName
                };

                string requestJson = JsonUtility.ToJson(request);
                string responseJson = await HttpClient.PostJson(ttsEndpoint, requestJson);

                var response = JsonUtility.FromJson<TTSResponse>(responseJson);

                if (string.IsNullOrEmpty(response.audio_url))
                {
                    Debug.LogError("[TTS] No audio URL received");
                    return;
                }

                // Download and play audio
                await DownloadAndPlay(response.audio_url);
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[TTS] Error: {e.Message}");
            }
        }

        /// <summary>
        /// Download audio file from URL and play it.
        /// </summary>
        private async Task DownloadAndPlay(string url)
        {
            using (var request = UnityWebRequestMultimedia.GetAudioClip(url, AudioType.MPEG))
            {
                var operation = request.SendWebRequest();

                // Wait for download
                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                if (request.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"[TTS] Failed to download audio: {request.error}");
                    return;
                }

                AudioClip clip = DownloadHandlerAudioClip.GetContent(request);
                audioSource.clip = clip;
                audioSource.Play();

                Debug.Log($"[TTS] Playing audio: {url}");
            }
        }

        /// <summary>
        /// Stop current playback.
        /// </summary>
        public void Stop()
        {
            audioSource.Stop();
        }
    }
}

