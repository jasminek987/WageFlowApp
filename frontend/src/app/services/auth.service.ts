// src/app/services/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, map, tap, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export type Role = 'manager' | 'employee';

export interface LoginResponse { token: string; role: Role; }
export interface Me { id: number; name: string; email: string; rate: number; }
export interface Timesheet {
  id: number;
  employeeId: number;
  weekStart: string;
  weekEnd?: string | null;
  hours: number;
  status: 'pending' | 'approved';
}
export interface Payslip {
  id: number;
  period: string;   // "YYYY-MM-DD to YYYY-MM-DD"
  gross: number;    // gross_pay
  net: number;      // net_pay
  tax?: number;     // tax_deductions
  start?: string;   // period_start
  end?: string;     // period_end
  pdfUrl?: string;  // still exposed but we won't open it
}
export interface Employee { id: number; name: string; email: string; rate: number; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(private http: HttpClient) {}

  // ---------- auth & storage ----------
  login(email: string, password: string, _role?: Role): Observable<LoginResponse> {
    const body = { email, password }; // backend decides role
    return this.http.post<LoginResponse>(`${environment.apiBase}/auth/login`, body)
      .pipe(tap(res => this.saveLogin(res.token, res.role)));
  }

  saveLogin(token: string, role: Role): void {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
  }

  token(): string | null { return localStorage.getItem('token'); }
  role(): Role | null { return (localStorage.getItem('role') as Role) || null; }

  private authHeaders(): HttpHeaders {
    const t = this.token();
    return new HttpHeaders(t ? { Authorization: `Bearer ${t}` } : {});
  }

  get isLoggedIn(): boolean { return !!this.token(); }

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
  }

  // ---------- normalizers ----------
  private normalizeTimesheet = (r: any): Timesheet => ({
    id: Number(r.id),
    employeeId: Number(r.employeeId ?? r.employee_id),
    weekStart: String(r.weekStart ?? r.week_start ?? ''),
    weekEnd: (r.weekEnd ?? r.week_end ?? null) as string | null,
    hours: Number(r.hours ?? r.total_hours ?? 0),
    status: String(r.status || '').toLowerCase() as 'pending' | 'approved',
  });

  private normalizePayslip = (r: any): Payslip => {
    const start = String(r.period_start ?? r.ps ?? '');
    const end   = String(r.period_end   ?? r.pe ?? '');
    return {
      id: Number(r.id),
      period: r.period ? String(r.period) : `${start} to ${end}`,
      gross: Number(r.gross ?? r.gross_pay ?? 0),
      net: Number(r.net ?? r.net_pay ?? 0),
      tax: Number(r.tax ?? r.tax_deductions ?? 0),
      start,
      end,
      pdfUrl: `${environment.apiBase}/payslips/${r.id}/pdf`,
    };
  };

  // ---------- employee-side ----------
  getMe(): Observable<Me> {
    return this.http
      .get<any>(`${environment.apiBase}/auth/me`, { headers: this.authHeaders() })
      .pipe(map(r => {
        const id = Number(r?.employee_id ?? r?.user_id);
        const name = String(r?.full_name ?? r?.name ?? r?.email ?? '');
        const email = String(r?.email ?? '');
        const rate = Number(r?.rate ?? 0);
        return { id, name, email, rate };
      }));
  }

  getMyTimesheets(): Observable<Timesheet[]> {
    return this.http
      .get<any[]>(`${environment.apiBase}/timesheets/me`, { headers: this.authHeaders() })
      .pipe(map(arr => (arr || []).map(this.normalizeTimesheet)));
  }

  getMyPayslips(): Observable<Payslip[]> {
    return this.http
      .get<any[]>(`${environment.apiBase}/payslips/me`, { headers: this.authHeaders() })
      .pipe(map(arr => (arr || []).map(this.normalizePayslip)));
  }

  payslipPdfUrl(id: number) {
    return `${environment.apiBase}/payslips/${id}/pdf`;
  }

  // ---------- manager-side ----------
  getEmployees(): Observable<Employee[]> {
    return this.http.get<Employee[]>(
      `${environment.apiBase}/employees/`,
      { headers: this.authHeaders() }
    );
  }

  getTimesheets(latestOnly = false): Observable<Timesheet[]> {
    const q = latestOnly ? '?latest=1' : '';
    return this.http
      .get<any[]>(`${environment.apiBase}/timesheets${q}`, { headers: this.authHeaders() })
      .pipe(map(arr => (arr || []).map(this.normalizeTimesheet)));
  }

  approveTimesheet(id: number): Observable<{ ok: boolean }> {
    const url = `${environment.apiBase}/timesheets/${id}/approve`;
    return this.http.patch<{ ok: boolean }>(url, {}, { headers: this.authHeaders() })
      .pipe(
        catchError(err => {
          if (err?.status === 0 || err?.status === 404 || err?.status === 405) {
            return this.http.post<{ ok: boolean }>(url, {}, { headers: this.authHeaders() });
          }
          return throwError(() => err);
        })
      );
  }

  createEmployee(payload: { name: string; email: string; rate: number }): Observable<Employee> {
    return this.http.post<Employee>(
      `${environment.apiBase}/employees/`,
      payload,
      { headers: this.authHeaders() }
    );
  }
}
