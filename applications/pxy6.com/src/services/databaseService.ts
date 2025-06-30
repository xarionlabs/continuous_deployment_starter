// API service for database operations via app.pxy6.com
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';

interface ApiResponse<T = any> {
  data: T | null;
  error: Error | null;
}

export const insertWaitingList = async (email: string, source?: string): Promise<ApiResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/waitlist`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, source }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return { data, error: null };
  } catch (error) {
    console.error('Error submitting to waitlist:', error);
    return { data: null, error: error as Error };
  }
};

export const insertFollowUpInfo = async (data: {
  email: string;
  role?: string;
  role_other?: string;
  platforms?: string[];
  monthly_traffic?: string;
  website_name?: string;
}): Promise<ApiResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/follow-up`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    return { data: result, error: null };
  } catch (error) {
    console.error('Error submitting follow-up data:', error);
    return { data: null, error: error as Error };
  }
};

export const insertLoiClick = async (email: string): Promise<ApiResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/loi-click`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return { data, error: null };
  } catch (error) {
    console.error('Error tracking LOI click:', error);
    return { data: null, error: error as Error };
  }
};