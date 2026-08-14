import axios from "axios";

// Create a configured Axios instance
export const api = axios.create({
  baseURL: "/api/v1", // Leverages the rewrite proxy defined in next.config.ts
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000, // 10s timeout
});

// Optional: Global response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Backend returned 409 (Conflict), 422 (Unprocessable Entity), or 429 (Rate Limit)
      console.error(`API Error ${error.response.status}:`, error.response.data);
    } else if (error.request) {
      console.error("No response received from backend:", error.request);
    } else {
      console.error("Axios config error:", error.message);
    }
    return Promise.reject(error);
  }
);
