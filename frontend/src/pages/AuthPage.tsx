import React, { FormEvent, useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/auth';
import { Mail, KeyRound, CheckCircle2, ArrowLeft, AlertCircle, Lock } from 'lucide-react';

type AuthMode = 'login' | 'register' | 'forgot' | 'reset';

export const AuthPage: React.FC = () => {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<AuthMode>('login');

  // Form states
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Password reset token states
  const [resetToken, setResetToken] = useState('');
  const [verifyingToken, setVerifyingToken] = useState(false);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  const [maskedEmail, setMaskedEmail] = useState<string | null>(null);

  // Status feedback
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Detect ?token=... in URL for password reset flow
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tokenFromUrl = params.get('token');
    if (tokenFromUrl) {
      setMode('reset');
      setResetToken(tokenFromUrl);
      setVerifyingToken(true);
      authApi
        .verifyResetToken(tokenFromUrl)
        .then((res) => {
          if (!res.valid) {
            setError(res.message || 'This password reset link is invalid or has expired.');
            setTokenValid(false);
          } else {
            setTokenValid(true);
            if (res.email) setMaskedEmail(res.email);
          }
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Unable to verify reset token.');
          setTokenValid(false);
        })
        .finally(() => {
          setVerifyingToken(false);
        });
    }
  }, []);

  const switchMode = (newMode: AuthMode) => {
    setError(null);
    setSuccessMessage(null);
    setPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setMode(newMode);
    if (window.location.search.includes('token=')) {
      window.history.replaceState({}, '', window.location.pathname);
    }
  };

  const handleLoginOrRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (mode === 'register') {
        await register(username, email, password);
      } else {
        await login(username, password);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to authenticate. Please check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgotPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setSubmitting(true);

    try {
      const res = await authApi.forgotPassword(email.trim());
      setSuccessMessage(res.message);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Failed to send reset link. Please verify your email.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (newPassword.length < 12) {
      setError('Password must be at least 12 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);

    try {
      const res = await authApi.resetPassword(resetToken, newPassword);
      setSuccessMessage(res.message);
      setTokenValid(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Failed to reset password. The link may have expired.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-sm">
              CIQ
            </span>
            <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">ChurnIQ</p>
          </div>

          <h1 className="mt-3 text-2xl font-bold text-slate-900">
            {mode === 'register' && 'Create your account'}
            {mode === 'login' && 'Sign in to your account'}
            {mode === 'forgot' && 'Reset your password'}
            {mode === 'reset' && 'Set a new password'}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {mode === 'register' && 'Register to securely manage customer churn insights.'}
            {mode === 'login' && 'Use your ChurnIQ account to access customer analytics.'}
            {mode === 'forgot' &&
              "Enter your registered email address and we'll send you a secure link to reset your password."}
            {mode === 'reset' &&
              (maskedEmail
                ? `Enter a strong new password for ${maskedEmail}.`
                : 'Enter your new password below to regain access to your account.')}
          </p>
        </div>

        {/* ── FORGOT PASSWORD MODE ─────────────────────────────────── */}
        {mode === 'forgot' && (
          <div>
            {successMessage ? (
              <div className="space-y-6">
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-900">
                  <div className="flex items-start space-x-3">
                    <CheckCircle2 className="h-6 w-6 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-emerald-800">Check your inbox</h3>
                      <p className="mt-1 text-sm text-emerald-700 leading-relaxed">
                        {successMessage}
                      </p>
                      <p className="mt-2 text-xs text-emerald-600">
                        Didn't see it? Check your spam folder or ensure the email address you entered is correct.
                      </p>
                    </div>
                  </div>
                </div>

                <button
                  className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700"
                  onClick={() => switchMode('login')}
                  type="button"
                >
                  Return to sign in
                </button>
              </div>
            ) : (
              <form className="space-y-5" onSubmit={handleForgotPassword}>
                <label className="block text-sm font-medium text-slate-700">
                  Email Address
                  <div className="relative mt-1">
                    <input
                      autoComplete="email"
                      autoFocus
                      className="block w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 placeholder-slate-400"
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="analyst@churniq.io"
                      required
                      type="email"
                      value={email}
                    />
                    <Mail className="absolute left-3 top-2.5 h-5 w-5 text-slate-400 pointer-events-none" />
                  </div>
                </label>

                {error && (
                  <div className="flex items-start space-x-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
                    <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60 flex items-center justify-center space-x-2"
                  disabled={submitting}
                  type="submit"
                >
                  {submitting ? (
                    <span>Sending instructions...</span>
                  ) : (
                    <>
                      <Mail className="h-4 w-4" />
                      <span>Send reset link</span>
                    </>
                  )}
                </button>

                <div className="text-center pt-2">
                  <button
                    className="inline-flex items-center space-x-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700"
                    onClick={() => switchMode('login')}
                    type="button"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    <span>Back to sign in</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* ── RESET PASSWORD MODE ─────────────────────────────────── */}
        {mode === 'reset' && (
          <div>
            {verifyingToken ? (
              <div className="flex flex-col items-center justify-center py-8 space-y-3">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
                <p className="text-sm text-slate-600">Verifying reset token...</p>
              </div>
            ) : successMessage ? (
              <div className="space-y-6">
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-900">
                  <div className="flex items-start space-x-3">
                    <CheckCircle2 className="h-6 w-6 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-emerald-800">Password Reset Complete!</h3>
                      <p className="mt-1 text-sm text-emerald-700 leading-relaxed">
                        {successMessage}
                      </p>
                    </div>
                  </div>
                </div>

                <button
                  className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700"
                  onClick={() => switchMode('login')}
                  type="button"
                >
                  Sign in with new password
                </button>
              </div>
            ) : tokenValid === false ? (
              <div className="space-y-5">
                <div className="flex items-start space-x-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900">
                  <AlertCircle className="h-6 w-6 text-rose-600 shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-rose-800">Invalid or Expired Link</h3>
                    <p className="mt-1 text-sm text-rose-700">
                      {error || 'This password reset link is invalid, has expired, or has already been used.'}
                    </p>
                  </div>
                </div>

                <button
                  className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700"
                  onClick={() => switchMode('forgot')}
                  type="button"
                >
                  Request a new reset link
                </button>

                <div className="text-center pt-2">
                  <button
                    className="inline-flex items-center space-x-1.5 text-sm font-semibold text-slate-600 hover:text-slate-800"
                    onClick={() => switchMode('login')}
                    type="button"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    <span>Back to sign in</span>
                  </button>
                </div>
              </div>
            ) : (
              <form className="space-y-5" onSubmit={handleResetPassword}>
                <label className="block text-sm font-medium text-slate-700">
                  New Password
                  <div className="relative mt-1">
                    <input
                      autoComplete="new-password"
                      autoFocus
                      className="block w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                      minLength={12}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="At least 12 characters"
                      required
                      type="password"
                      value={newPassword}
                    />
                    <Lock className="absolute left-3 top-2.5 h-5 w-5 text-slate-400 pointer-events-none" />
                  </div>
                  <span className="mt-1 block text-xs text-slate-500">Minimum 12 characters.</span>
                </label>

                <label className="block text-sm font-medium text-slate-700">
                  Confirm New Password
                  <div className="relative mt-1">
                    <input
                      autoComplete="new-password"
                      className="block w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                      minLength={12}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm your password"
                      required
                      type="password"
                      value={confirmPassword}
                    />
                    <KeyRound className="absolute left-3 top-2.5 h-5 w-5 text-slate-400 pointer-events-none" />
                  </div>
                </label>

                {error && (
                  <div className="flex items-start space-x-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
                    <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60 flex items-center justify-center space-x-2"
                  disabled={submitting}
                  type="submit"
                >
                  {submitting ? (
                    <span>Updating password...</span>
                  ) : (
                    <>
                      <KeyRound className="h-4 w-4" />
                      <span>Set new password</span>
                    </>
                  )}
                </button>

                <div className="text-center pt-2">
                  <button
                    className="inline-flex items-center space-x-1.5 text-sm font-semibold text-slate-600 hover:text-slate-800"
                    onClick={() => switchMode('login')}
                    type="button"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    <span>Back to sign in</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* ── LOGIN & REGISTER MODES ───────────────────────────────── */}
        {(mode === 'login' || mode === 'register') && (
          <div>
            <form className="space-y-5" onSubmit={handleLoginOrRegister}>
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

              {mode === 'register' && (
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

              <div>
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium text-slate-700">
                    Password
                  </label>
                  {mode === 'login' && (
                    <button
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                      onClick={() => switchMode('forgot')}
                      type="button"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <input
                  autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  minLength={mode === 'register' ? 12 : 1}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
                {mode === 'register' && (
                  <span className="mt-1 block text-xs text-slate-500">Use at least 12 characters.</span>
                )}
              </div>

              {error && (
                <div className="flex items-start space-x-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
                  <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <button
                className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={submitting}
                type="submit"
              >
                {submitting
                  ? 'Please wait...'
                  : mode === 'register'
                  ? 'Create account'
                  : 'Sign in'}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-slate-600">
              {mode === 'register' ? 'Already have an account?' : 'New to ChurnIQ?'}{' '}
              <button
                className="font-semibold text-indigo-600 hover:text-indigo-700"
                onClick={() => switchMode(mode === 'register' ? 'login' : 'register')}
                type="button"
              >
                {mode === 'register' ? 'Sign in' : 'Create an account'}
              </button>
            </p>
          </div>
        )}
      </section>
    </main>
  );
};
