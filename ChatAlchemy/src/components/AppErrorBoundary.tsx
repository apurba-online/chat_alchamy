import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export class AppErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  public state = { hasError: false };

  public static getDerivedStateFromError() {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ChatAlchemy uncaught application error', error, errorInfo);
  }

  public render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6 dark:bg-slate-950">
        <section className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-7 shadow-xl shadow-slate-950/5 dark:border-slate-800 dark:bg-slate-900">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-300"><AlertTriangle className="h-5 w-5" /></span>
          <h1 className="mt-5 text-xl font-semibold text-slate-950 dark:text-white">The research workspace hit an unexpected error.</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">No biomedical conclusion should be inferred from an interrupted workflow. Reload the application and run the query again.</p>
          <button onClick={() => window.location.reload()} className="mt-5 inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white dark:bg-white dark:text-slate-950"><RefreshCw className="h-4 w-4" />Reload workspace</button>
        </section>
      </main>
    );
  }
}
