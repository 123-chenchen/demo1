import React, { useState } from 'react';
import { CheckCircle2, Languages, Lock, LogOut, Moon, Sun, Trash2, User } from 'lucide-react';

import { useAppContext } from '../../app/AppContext.jsx';

export function SettingsPage() {
  const { settings } = useAppContext();
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_new_password: '',
  });
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteConfirmation, setDeleteConfirmation] = useState('');

  const user = settings.user;
  const displayName = resolveUserDisplayName(user);
  const isVietnamese = settings.values.language === 'vi';
  const text = isVietnamese ? viText : enText;

  async function submitPasswordChange(event) {
    event.preventDefault();
    await settings.onChangePassword(passwordForm);
    setPasswordForm({
      current_password: '',
      new_password: '',
      confirm_new_password: '',
    });
  }

  async function submitDeleteAccount(event) {
    event.preventDefault();
    await settings.onDeleteAccount({ current_password: deletePassword });
    setDeletePassword('');
    setDeleteConfirmation('');
  }

  return (
    <main className="mx-auto grid min-h-[calc(100vh-154px)] max-w-5xl gap-4 overflow-visible px-4 py-4 pb-12 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:px-6">
      <section className="space-y-4">
        <Panel title={text.accountProfile} icon={User}>
          <dl className="space-y-3 text-sm">
            <ProfileRow label={text.email} value={user?.email || text.unknown} />
            <ProfileRow label={text.name} value={displayName || text.notSet} />
          </dl>
          {!settings.isAuthDisabled && (
            <button
              type="button"
              className="mt-4 inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-bold text-zinc-700 hover:border-teal-300 hover:text-teal-800"
              onClick={settings.onLogout}
            >
              <LogOut size={16} />
              {text.signOut}
            </button>
          )}
        </Panel>

        <Panel title={text.preferences} icon={Languages}>
          <SettingGroup label={text.language}>
            <SegmentedButton
              active={settings.values.language === 'en'}
              disabled={settings.isSaving}
              onClick={() => settings.onUpdate({ language: 'en' })}
            >
              English
            </SegmentedButton>
            <SegmentedButton
              active={settings.values.language === 'vi'}
              disabled={settings.isSaving}
              onClick={() => settings.onUpdate({ language: 'vi' })}
            >
              Tiếng Việt
            </SegmentedButton>
          </SettingGroup>

          <SettingGroup label={text.theme}>
            <SegmentedButton
              active={settings.values.theme === 'light'}
              disabled={settings.isSaving}
              onClick={() => settings.onUpdate({ theme: 'light' })}
            >
              <Sun size={15} />
              {text.lightMode}
            </SegmentedButton>
            <SegmentedButton
              active={settings.values.theme === 'dark'}
              disabled={settings.isSaving}
              onClick={() => settings.onUpdate({ theme: 'dark' })}
            >
              <Moon size={15} />
              {text.darkMode}
            </SegmentedButton>
          </SettingGroup>

          {settings.message && (
            <p className="mt-4 inline-flex items-center gap-2 rounded-md bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">
              <CheckCircle2 size={16} />
              {settings.message}
            </p>
          )}
        </Panel>
      </section>

      <section className="space-y-4">
        <Panel title={text.changePassword} icon={Lock}>
          <form className="space-y-3" onSubmit={submitPasswordChange}>
            <PasswordInput
              label={text.currentPassword}
              value={passwordForm.current_password}
              onChange={(value) => setPasswordForm((current) => ({ ...current, current_password: value }))}
              disabled={settings.isAuthDisabled || settings.isChangingPassword}
            />
            <PasswordInput
              label={text.newPassword}
              value={passwordForm.new_password}
              onChange={(value) => setPasswordForm((current) => ({ ...current, new_password: value }))}
              disabled={settings.isAuthDisabled || settings.isChangingPassword}
            />
            <PasswordInput
              label={text.confirmNewPassword}
              value={passwordForm.confirm_new_password}
              onChange={(value) => setPasswordForm((current) => ({ ...current, confirm_new_password: value }))}
              disabled={settings.isAuthDisabled || settings.isChangingPassword}
            />
            <button
              className="inline-flex items-center justify-center rounded-lg bg-zinc-950 px-4 py-2.5 text-sm font-bold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
              disabled={
                settings.isAuthDisabled ||
                settings.isChangingPassword ||
                !passwordForm.current_password ||
                !passwordForm.new_password ||
                !passwordForm.confirm_new_password
              }
            >
              {settings.isChangingPassword ? text.saving : text.updatePassword}
            </button>
          </form>
        </Panel>

        <Panel title={text.deleteAccount} icon={Trash2}>
          <form className="space-y-3" onSubmit={submitDeleteAccount}>
            <PasswordInput
              label={text.currentPassword}
              value={deletePassword}
              onChange={setDeletePassword}
              disabled={settings.isAuthDisabled || settings.isDeletingAccount}
            />
            <label className="block text-sm">
              <span className="font-semibold text-zinc-700">{text.typeDelete}</span>
              <input
                className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-rose-500 focus:ring-4 focus:ring-rose-100"
                value={deleteConfirmation}
                onChange={(event) => setDeleteConfirmation(event.target.value)}
                disabled={settings.isAuthDisabled || settings.isDeletingAccount}
              />
            </label>
            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
              disabled={settings.isAuthDisabled || settings.isDeletingAccount || !deletePassword || deleteConfirmation !== 'DELETE'}
            >
              <Trash2 size={16} />
              {settings.isDeletingAccount ? text.deleting : text.deleteAccount}
            </button>
          </form>
        </Panel>
      </section>
    </main>
  );
}

function Panel({ title, icon: Icon, children }) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <div className="rounded-lg bg-zinc-100 p-2 text-zinc-700">
          <Icon size={18} />
        </div>
        <h2 className="text-lg font-bold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function ProfileRow({ label, value }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="truncate font-semibold text-zinc-900">{value}</dd>
    </div>
  );
}

function SettingGroup({ label, children }) {
  return (
    <div className="mt-4">
      <p className="mb-2 text-sm font-semibold text-zinc-700">{label}</p>
      <div className="inline-flex flex-wrap gap-1 rounded-lg border border-zinc-200 bg-zinc-50 p-1">{children}</div>
    </div>
  );
}

function SegmentedButton({ active, disabled, onClick, children }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-bold transition ${
        active ? 'bg-white text-teal-800 shadow-sm ring-1 ring-zinc-200' : 'text-zinc-600 hover:bg-white hover:text-zinc-900'
      }`}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function PasswordInput({ label, value, onChange, disabled }) {
  return (
    <label className="block text-sm">
      <span className="font-semibold text-zinc-700">{label}</span>
      <input
        className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
        type="password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
      />
    </label>
  );
}

function resolveUserDisplayName(user) {
  const profileName = user?.profile?.name || user?.google_profile?.name || user?.googleProfile?.name;
  const value = user?.name || user?.full_name || profileName || emailPrefix(user?.email);
  return typeof value === 'string' ? value.trim() : '';
}

function emailPrefix(email) {
  if (!email) return '';
  return email.split('@')[0].split('+')[0].replace(/[._-]+/g, ' ').trim();
}

const enText = {
  accountProfile: 'Account / Profile',
  profile: 'Profile',
  preferences: 'Preferences',
  email: 'Email',
  name: 'Name',
  unknown: 'Unknown',
  notSet: 'Not set',
  language: 'Language',
  theme: 'Theme',
  lightMode: 'Light mode',
  darkMode: 'Dark mode',
  changePassword: 'Change Password',
  currentPassword: 'Current password',
  newPassword: 'New password',
  confirmNewPassword: 'Confirm new password',
  saving: 'Saving...',
  updatePassword: 'Update password',
  deleteAccount: 'Delete Account',
  typeDelete: 'Type DELETE to confirm',
  deleting: 'Deleting...',
  signOut: 'Sign out',
};

const viText = {
  accountProfile: 'Tài khoản / Hồ sơ',
  signOut: 'Đăng xuất',
  profile: 'Hồ sơ',
  preferences: 'Tùy chọn',
  email: 'Email',
  name: 'Tên',
  unknown: 'Không rõ',
  notSet: 'Chưa đặt',
  language: 'Ngôn ngữ',
  theme: 'Giao diện',
  lightMode: 'Chế độ sáng',
  darkMode: 'Chế độ tối',
  changePassword: 'Đổi mật khẩu',
  currentPassword: 'Mật khẩu hiện tại',
  newPassword: 'Mật khẩu mới',
  confirmNewPassword: 'Xác nhận mật khẩu mới',
  saving: 'Đang lưu...',
  updatePassword: 'Cập nhật mật khẩu',
  deleteAccount: 'Xóa tài khoản',
  typeDelete: 'Nhập DELETE để xác nhận',
  deleting: 'Đang xóa...',
};
