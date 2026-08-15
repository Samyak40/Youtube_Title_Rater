export interface ScoreResponse {
  engagement_score: number;
  percentile: number;
  raw_prediction: number;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function scoreTitle(title: string): Promise<ScoreResponse> {
  const response = await fetch(`${API_URL}/score`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `API error: ${response.status}`);
  }

  return response.json();
}
