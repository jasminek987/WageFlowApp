// src/main.ts
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, withEnabledBlockingInitialNavigation } from '@angular/router';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';

import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';
import { TokenInterceptor } from './app/services/token.interceptor';

bootstrapApplication(AppComponent, {
  providers: [
    provideRouter(routes, withEnabledBlockingInitialNavigation()),
    // Use HttpClient with interceptors provided from DI
    provideHttpClient(withInterceptorsFromDi()),
    // Register your token interceptor
    { provide: HTTP_INTERCEPTORS, useClass: TokenInterceptor, multi: true },
  ],
}).catch(console.error);
