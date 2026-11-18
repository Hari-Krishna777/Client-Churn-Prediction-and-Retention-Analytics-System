import React, { FormEvent, useState } from 'react';
import { useAuth } from '../context/AuthContext';

export const AuthPage: React.FC = () => {
  const { login, register } = useAuth();
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (isRegistering) {
        await register(username, email, password);
      } else {
        await login(username, password);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to authenticate. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
        <div className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">ChurnIQ</p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">
            {isRegistering ? 'Create your account' : 'Sign in to your account'}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {isRegistering
              ? 'Register to securely manage customer churn insights.'
              : 'Use your ChurnIQ account to access customer analytics.'}
          </p>
        </div>

        <form className="space-y-5" onSubmit={submit}>
          <label className="block text-sm font-medium text-slate-700">
            Username
            <input
              autoComplete="username"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              maxLength={100}
              minLength={3}
              onChange={(event) => setUsername(event.target.value)}
              required
              value={username}
            />
          </label>

          {isRegistering && (
            <label className="block text-sm font-medium text-slate-700">
              Email
              <input
                autoComplete="email"
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
            </label>
          )}

          <label className="block text-sm font-medium text-slate-700">
            Password
            <input
              autoComplete={isRegistering ? 'new-password' : 'current-password'}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              minLength={isRegistering ? 12 : 1}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
            {isRegistering && (
              <span className="mt-1 block text-xs text-slate-500">Use at least 12 characters.</span>
            )}
          </label>

          {error && (
            <p aria-live="polite" className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          )}

          <button
            className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={submitting}
            type="submit"
          >
            {submitting ? 'Please wait...' : isRegistering ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600">
          {isRegistering ? 'Already have an account?' : 'New to ChurnIQ?'}{' '}
          <button
            className="font-semibold text-indigo-600 hover:text-indigo-700"
            onClick={() => {
              setError(null);
              setPassword('');
              setIsRegistering(!isRegistering);
            }}
            type="button"
          >
            {isRegistering ? 'Sign in' : 'Create an account'}
          </button>
        </p>
      </section>
    </main>
  );
};
