// src/app/app.routes.ts
import { Routes, CanActivateFn } from '@angular/router';
import { inject } from '@angular/core';
import { Router } from '@angular/router';

import { LoginComponent } from './login/login.component';
import { ManagerDashboardComponent } from './manager-dashboard/manager-dashboard.component';
import { EmployeeDashboardComponent } from './employee-dashboard/employee-dashboard.component';
import { AuthService } from './services/auth.service';

// Require a token
const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.token()) {
    router.navigate(['/login']);
    return false;
  }
  return true;
};

// Role guards
const managerOnly: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.role() !== 'manager') {
    router.navigate(['/employee-dashboard']);
    return false;
  }
  return true;
};

const employeeOnly: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.role() !== 'employee') {
    router.navigate(['/manager-dashboard']);
    return false;
  }
  return true;
};

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: 'login', component: LoginComponent },

  {
    path: 'manager-dashboard',
    component: ManagerDashboardComponent,
    canActivate: [authGuard, managerOnly],
  },
  {
    path: 'employee-dashboard',
    component: EmployeeDashboardComponent,
    canActivate: [authGuard, employeeOnly],
  },

  { path: '**', redirectTo: 'login' },
];
