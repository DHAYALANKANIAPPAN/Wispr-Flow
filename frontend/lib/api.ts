/**
 * API client library for Adaptive IQ.
 * Communicates strictly with the FastAPI backend endpoints.
 * Fails closed with descriptive errors when the server is unreachable.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'student' | 'teacher';
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Concept {
  id: string;
  name: string;
  description: string;
  is_unlocked: boolean;
  unlocked?: boolean;
  mastery?: number;
  prerequisites: string[];
}

export interface QuestionData {
  id: string;
  text: string;
  answer_type: 'numeric' | 'text';
  difficulty: 1 | 2 | 3;
  question_type: 'conceptual' | 'numerical';
  rubric?: string;
  concept_ids: string[];
}

export interface NextQuestionResponse {
  question_id: string | null;
  concept_id: string | null;
  reason: {
    rule: string;
    concept: string;
    mastery: number;
    detail: string;
  };
  question?: QuestionData;
}

export interface SubmitAttemptResponse {
  attempt_id: string;
  correct: boolean;
  reasoning: 'sound' | 'weak' | 'none';
  misconception_id: string | null;
  evidence: number;
  llm_status: 'ok' | 'skipped' | 'unavailable' | 'invalid_output';
  feedback: string;
  concept_mastery_updates: Record<
    string,
    {
      mastery_before: number;
      mastery_after: number;
      change: number;
    }
  >;
  next_question: {
    question_id: string | null;
    concept_id: string | null;
    reason: {
      rule: string;
      concept: string;
      mastery: number;
      detail: string;
    };
  };
}

export interface StudentMasterySummary {
  student_id: string;
  concept_mastery: Record<
    string,
    {
      name: string;
      mastery: number;
      percentage: number;
      attempts_count: number;
    }
  >;
  weakest_concept: string | null;
  strongest_concept: string | null;
  total_attempts: number;
  accuracy_percentage: number;
  upcoming_revisions: Array<{
    concept_id: string;
    concept_name: string;
    due_date: string;
    rule: string;
  }>;
  misconceptions_encountered: Array<{
    misconception_id: string;
    count: number;
  }>;
}

export interface DecisionLogRecord {
  id: string;
  student_id: string;
  decision_type: string;
  payload: {
    rule: string;
    concept: string;
    mastery?: number;
    detail?: string;
    [key: string]: any;
  };
  created_at: string;
}

export interface TeacherClassSummary {
  teacher_id: string;
  total_students: number;
  total_attempts: number;
  average_class_accuracy: number;
  concept_class_mastery: Record<
    string,
    {
      concept_name: string;
      average_mastery: number;
      average_percentage: number;
      students_assessed: number;
    }
  >;
  most_missed_concept: string | null;
  students_needing_support: Array<{
    student_id: string;
    student_name?: string;
    name?: string;
    weakest_concept: string;
    weakest_mastery?: number;
    average_mastery?: number;
    flag_reason?: string;
  }>;
  misconception_distribution: Record<string, number>;
}

class ApiService {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('adaptive_iq_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('adaptive_iq_token', token);
      } else {
        localStorage.removeItem('adaptive_iq_token');
      }
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('adaptive_iq_token');
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const url = `${API_BASE_URL}${endpoint}`;
    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorDetail = `Request failed with status ${response.status}`;
        try {
          const errData = await response.json();
          if (errData.detail) {
            errorDetail = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
          }
        } catch (_) {}
        throw new Error(errorDetail);
      }

      return (await response.json()) as T;
    } catch (err: any) {
      if (err.message && err.message.includes('Failed to fetch')) {
        throw new Error(
          `Cannot reach backend server at ${API_BASE_URL}. Ensure the backend service is running on port 8000.`
        );
      }
      throw err;
    }
  }

  async checkHealth(): Promise<{ status: string; service: string }> {
    return this.request<{ status: string; service: string }>('/health');
  }

  async register(data: { name: string; email: string; password: string; role: 'student' | 'teacher' }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(res.access_token);
    return res;
  }

  async login(data: { email: string; password: string }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(res.access_token);
    return res;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  logout() {
    this.setToken(null);
  }

  async getConcepts(): Promise<Concept[]> {
    return this.request<Concept[]>('/concepts');
  }

  async getNextQuestion(): Promise<NextQuestionResponse> {
    return this.request<NextQuestionResponse>('/questions/next');
  }

  async submitAttempt(data: {
    question_id: string;
    student_answer: string;
    explanation: string;
  }): Promise<SubmitAttemptResponse> {
    return this.request<SubmitAttemptResponse>('/attempts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getStudentMastery(studentId: string): Promise<StudentMasterySummary> {
    return this.request<StudentMasterySummary>(`/students/${studentId}/mastery`);
  }

  async getStudentDecisions(studentId: string, limit = 50): Promise<DecisionLogRecord[]> {
    return this.request<DecisionLogRecord[]>(`/students/${studentId}/decisions?limit=${limit}`);
  }

  async getTeacherClassSummary(teacherId: string): Promise<TeacherClassSummary> {
    return this.request<TeacherClassSummary>(`/teachers/${teacherId}/class-summary`);
  }
}

export const api = new ApiService();
