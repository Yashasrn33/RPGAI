/*
 * HTTP Client for RPGAI
 * Handles JSON POST/GET requests to the Python backend using UnityWebRequest.
 */

using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System.Threading.Tasks;

namespace RPGAI.Net
{
    public static class HttpClient
    {
        /// <summary>
        /// Send a JSON POST request to the specified URL.
        /// </summary>
        /// <param name="url">The endpoint URL</param>
        /// <param name="json">JSON string to send in body</param>
        /// <returns>Response text from server</returns>
        public static async Task<string> PostJson(string url, string json)
        {
            using (var request = new UnityWebRequest(url, "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(json);
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");

                var operation = request.SendWebRequest();

                // Wait for completion
                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                if (request.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"HTTP POST failed: {request.error}\nURL: {url}");
                    throw new System.Exception($"HTTP Error: {request.error}");
                }

                return request.downloadHandler.text;
            }
        }

        /// <summary>
        /// Send a GET request to the specified URL.
        /// </summary>
        /// <param name="url">The endpoint URL with query params</param>
        /// <returns>Response text from server</returns>
        public static async Task<string> Get(string url)
        {
            using (var request = UnityWebRequest.Get(url))
            {
                var operation = request.SendWebRequest();

                // Wait for completion
                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                if (request.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"HTTP GET failed: {request.error}\nURL: {url}");
                    throw new System.Exception($"HTTP Error: {request.error}");
                }

                return request.downloadHandler.text;
            }
        }
    }
}

