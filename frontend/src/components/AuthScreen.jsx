import React, { useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  LockKeyhole,
  Mail,
  MessageSquareText,
  RotateCcw,
  ShieldCheck,
  UserPlus,
} from 'lucide-react';

const authCopy = {
  login: {
    title: 'Sign In',
    description: 'Access your document question-answering workspace.',
    button: 'Sign In',
    icon: KeyRound,
  },
  register: {
    title: 'Create Account',
    description: 'Use your email to receive an OTP and complete registration.',
    button: 'Send Registration OTP',
    icon: UserPlus,
  },
  verify: {
    title: 'Verify OTP',
    description: 'Enter the OTP sent to your email.',
    button: 'Verify OTP',
    icon: ShieldCheck,
  },
  reset: {
    title: 'Forgot Password',
    description: 'Enter your email to receive a password reset OTP.',
    button: 'Send Reset OTP',
    icon: RotateCcw,
  },
  'reset-verify': {
    title: 'Reset Password',
    description: 'Enter the OTP and a new account password.',
    button: 'Reset Password',
    icon: LockKeyhole,
  },
};

function AuthField({ icon: Icon, label, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-zinc-800">{label}</span>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={18} />
        {children}
      </div>
    </label>
  );
}

const baseInputClass =
  'w-full rounded-lg border border-zinc-200 bg-white py-3 pl-10 text-sm text-zinc-950 outline-none transition placeholder:text-zinc-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-100';

export function AuthScreen({
  mode,
  email,
  password,
  newPassword,
  otp,
  message,
  error,
  isLoading,
  onSubmit,
  onModeChange,
  onEmailChange,
  onPasswordChange,
  onNewPasswordChange,
  onOtpChange,
}) {
  const copy = authCopy[mode] || authCopy.login;
  const ModeIcon = copy.icon;
  const [showPassword, setShowPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const needsPassword = mode === 'login' || mode === 'register';
  const needsOtp = mode === 'verify' || mode === 'reset-verify';
  const isResetFlow = mode === 'reset' || mode === 'reset-verify';

  return (
    <div className="min-h-screen bg-zinc-100 text-zinc-950">
      <main className="mx-auto grid min-h-screen w-full max-w-6xl items-center gap-6 px-4 py-8 md:px-6 lg:grid-cols-[minmax(0,0.92fr)_minmax(380px,440px)]">
        <section className="hidden lg:block">
          <div className="max-w-xl">
            <div className="mb-8 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-teal-600 text-white shadow-sm">
                <MessageSquareText size={25} />
              </div>
              <div>
                <p className="text-sm font-semibold text-teal-700">PDF Chatbot</p>
                <h1 className="text-3xl font-bold leading-tight text-zinc-950">Sign in to continue working</h1>
              </div>
            </div>

            <div className="grid gap-3">
              <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-zinc-900">Documents</p>
                <p className="mt-1 text-sm leading-6 text-zinc-600">
                  Manage notebooks, PDFs, and question history in one workspace.
                </p>
              </div>
              <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-zinc-900">Workspace</p>
                <p className="mt-1 text-sm leading-6 text-zinc-600">
                  Keep your sources, conversations, and settings together across sessions.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-soft sm:p-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-zinc-950 text-white lg:hidden">
                <MessageSquareText size={23} />
              </div>
              <div>
                <p className="text-sm font-semibold text-teal-700 lg:hidden">PDF Chatbot</p>
                <h2 className="text-xl font-bold leading-tight">{copy.title}</h2>
                <p className="mt-1 text-sm leading-5 text-zinc-500">{copy.description}</p>
              </div>
            </div>

            <div className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700 sm:flex">
              <ModeIcon size={22} />
            </div>
          </div>

          {!needsOtp && !isResetFlow && (
            <div className="mt-6 grid grid-cols-2 rounded-lg bg-zinc-100 p-1">
              <button
                type="button"
                className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                  mode === 'login' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-800'
                }`}
                onClick={() => onModeChange('login')}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                  mode === 'register' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-800'
                }`}
                onClick={() => onModeChange('register')}
              >
                Register
              </button>
            </div>
          )}

          {error && (
            <div className="mt-5 flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm leading-5 text-rose-800">
              <AlertCircle className="mt-0.5 shrink-0" size={18} />
              <span>{error}</span>
            </div>
          )}

          {message && (
            <div className="mt-5 flex gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm leading-5 text-emerald-800">
              <CheckCircle2 className="mt-0.5 shrink-0" size={18} />
              <span>{message}</span>
            </div>
          )}

          <form className="mt-5 space-y-4" onSubmit={onSubmit}>
            <AuthField icon={Mail} label="Email">
              <input
                className={`${baseInputClass} pr-3`}
                value={email}
                onChange={(event) => onEmailChange(event.target.value)}
                placeholder="you@example.com"
                type="email"
                autoComplete="email"
                required
              />
            </AuthField>

            {needsPassword && (
              <AuthField icon={LockKeyhole} label="Password">
                <input
                  className={`${baseInputClass} pr-12`}
                  value={password}
                  onChange={(event) => onPasswordChange(event.target.value)}
                  placeholder="Enter your password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  minLength={8}
                  required
                />
                <button
                  type="button"
                  className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </AuthField>
            )}

            {needsOtp && (
              <AuthField icon={ShieldCheck} label="OTP Code">
                <input
                  className={`${baseInputClass} pr-3`}
                  value={otp}
                  onChange={(event) => onOtpChange(event.target.value)}
                  placeholder="000000"
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  minLength={4}
                  maxLength={12}
                  required
                />
              </AuthField>
            )}

            {mode === 'reset-verify' && (
              <AuthField icon={LockKeyhole} label="New Password">
                <input
                  className={`${baseInputClass} pr-12`}
                  value={newPassword}
                  onChange={(event) => onNewPasswordChange(event.target.value)}
                  placeholder="Enter a new password"
                  type={showNewPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
                <button
                  type="button"
                  className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800"
                  onClick={() => setShowNewPassword((current) => !current)}
                  aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                  title={showNewPassword ? 'Hide new password' : 'Show new password'}
                >
                  {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </AuthField>
            )}

            <button
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
              disabled={isLoading}
            >
              {isLoading ? <Loader2 className="animate-spin" size={18} /> : <ArrowRight size={18} />}
              {copy.button}
            </button>
          </form>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm">
            {(needsOtp || isResetFlow) && (
              <button
                type="button"
                className="inline-flex items-center gap-1.5 font-semibold text-zinc-600 hover:text-zinc-950"
                onClick={() => onModeChange('login')}
              >
                <ArrowLeft size={16} />
                Back to sign in
              </button>
            )}

            {mode === 'login' && (
              <button type="button" className="ml-auto font-semibold text-teal-700 hover:text-teal-800" onClick={() => onModeChange('reset')}>
                Forgot password?
              </button>
            )}

            {mode === 'register' && (
              <button type="button" className="ml-auto font-semibold text-teal-700 hover:text-teal-800" onClick={() => onModeChange('login')}>
                Already have an account?
              </button>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
