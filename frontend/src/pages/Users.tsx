import React, { useEffect, useState } from 'react';
import {
  changePassword,
  createRole,
  createUser,
  deleteRole,
  deleteUser,
  getAssignableRoles,
  getPermissionCatalog,
  getRoles,
  getUsers,
  updateRole,
  updateUser,
} from '../api/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { AuthUser, PermissionCatalog, RoleItem } from '../types';
import './Employees.css';

export const Users: React.FC = () => {
  const toast = useToast();
  const { isAdmin, user: currentUser } = useAuth();
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [assignableRoles, setAssignableRoles] = useState<RoleItem[]>([]);
  const [permissionCatalog, setPermissionCatalog] = useState<PermissionCatalog>({});
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('');
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [roleName, setRoleName] = useState('');
  const [rolePermissions, setRolePermissions] = useState<string[]>([]);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showCreatePassword, setShowCreatePassword] = useState(false);

  const load = () => getUsers().then(setUsers).catch(() => toast('Не удалось загрузить пользователей.', 'error'));
  useEffect(() => {
    void load();
    getAssignableRoles()
      .then((items) => {
        setAssignableRoles(items);
        setRole((current) => current || items[0]?.name || '');
      })
      .catch(() => toast('Не удалось загрузить доступные роли.', 'error'));
    if (isAdmin) {
      Promise.all([getRoles(), getPermissionCatalog()])
        .then(([roleItems, catalog]) => {
          setRoles(roleItems);
          setPermissionCatalog(catalog);
        })
        .catch(() => toast('Не удалось загрузить настройки ролей.', 'error'));
    }
  }, [isAdmin]);

  const chooseRole = (value: string) => {
    const selected = roles.find((item) => item.id === Number(value));
    setSelectedRoleId(selected?.id ?? null);
    setRoleName(selected?.name ?? '');
    setRolePermissions(selected?.permissions ?? []);
  };

  const startNewRole = () => {
    setSelectedRoleId(null);
    setRoleName('');
    setRolePermissions([]);
  };

  const toggleRolePermission = (permission: string) => {
    setRolePermissions((current) => current.includes(permission)
      ? current.filter((item) => item !== permission)
      : [...current, permission]);
  };

  const saveRole = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      if (selectedRoleId) {
        await updateRole(selectedRoleId, { name: roleName, permissions: rolePermissions });
        toast('Роль обновлена.', 'success');
      } else {
        const created = await createRole({ name: roleName, permissions: rolePermissions });
        setSelectedRoleId(created.id);
        toast('Роль создана.', 'success');
      }
      const [roleItems, assignableItems] = await Promise.all([getRoles(), getAssignableRoles()]);
      setRoles(roleItems);
      setAssignableRoles(assignableItems);
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось сохранить роль.', 'error');
    }
  };

  const removeRole = async () => {
    if (!selectedRoleId || !window.confirm('Удалить выбранную роль?')) return;
    try {
      await deleteRole(selectedRoleId);
      toast('Роль удалена.', 'success');
      startNewRole();
      const [roleItems, assignableItems] = await Promise.all([getRoles(), getAssignableRoles()]);
      setRoles(roleItems);
      setAssignableRoles(assignableItems);
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось удалить роль.', 'error');
    }
  };

  const changeUserRole = async (userId: number, nextRole: string) => {
    try {
      await updateUser(userId, { role: nextRole });
      toast('Роль пользователя изменена.', 'success');
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось изменить роль пользователя.', 'error');
    }
  };

  const add = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await createUser({ username, password, role, is_active: true });
      toast('Пользователь создан.', 'success');
      setUsername('');
      setPassword('');
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Ошибка создания пользователя', 'error');
    }
  };

  const changeOwnPassword = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await changePassword(currentPassword, newPassword);
      toast('Пароль изменён.', 'success');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось изменить пароль.', 'error');
    }
  };

  return (
    <div className="employees-page">
      <form className="detail-section" onSubmit={changeOwnPassword}>
        <h3>Изменить свой пароль</h3>
        <div className="fields-grid">
          <label className="detail-field">
            Текущий пароль
            <div className="password-field">
              <input
                type={showCurrentPassword ? 'text' : 'password'}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowCurrentPassword((value) => !value)}
                aria-label={showCurrentPassword ? 'Скрыть пароль' : 'Показать пароль'}
                title={showCurrentPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showCurrentPassword ? 'Скрыть' : 'Показать'}
              </button>
            </div>
          </label>
          <label className="detail-field">
            Новый пароль
            <div className="password-field">
              <input
                type={showNewPassword ? 'text' : 'password'}
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowNewPassword((value) => !value)}
                aria-label={showNewPassword ? 'Скрыть пароль' : 'Показать пароль'}
                title={showNewPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showNewPassword ? 'Скрыть' : 'Показать'}
              </button>
            </div>
          </label>
        </div>
        <div className="dashboard-actions" style={{ marginTop: 16 }}>
          <button className="btn-primary" type="submit">Сохранить пароль</button>
        </div>
      </form>
      <form className="detail-section" onSubmit={add}>
        <h3>Добавить пользователя</h3>
        <div className="fields-grid">
          <label className="detail-field">Логин<input value={username} onChange={(e) => setUsername(e.target.value)} required /></label>
          <label className="detail-field">
            Пароль
            <div className="password-field">
              <input
                type={showCreatePassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowCreatePassword((value) => !value)}
                aria-label={showCreatePassword ? 'Скрыть пароль' : 'Показать пароль'}
                title={showCreatePassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showCreatePassword ? 'Скрыть' : 'Показать'}
              </button>
            </div>
          </label>
          <label className="detail-field">Роль
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {assignableRoles.map((item) => <option key={item.id} value={item.name}>{item.name}</option>)}
            </select>
          </label>
        </div>
        <div className="dashboard-actions" style={{ marginTop: 16 }}>
          <button className="btn-primary" type="submit">Добавить</button>
        </div>
      </form>
      {isAdmin && (
        <form className="detail-section role-editor" onSubmit={saveRole}>
          <div className="role-editor-header">
            <h3>Настройка ролей</h3>
            <button className="btn-outline" type="button" onClick={startNewRole}>Новая роль</button>
          </div>
          <label className="detail-field role-picker">
            Выбрать роль для изменения
            <select value={selectedRoleId ?? ''} onChange={(event) => chooseRole(event.target.value)}>
              <option value="">Новая роль</option>
              {roles.map((item) => <option key={item.id} value={item.id}>{item.name}{item.is_system ? ' · системная' : ''}</option>)}
            </select>
          </label>
          <label className="detail-field role-name-field">
            Название роли
            <input value={roleName} onChange={(event) => setRoleName(event.target.value)} minLength={2} maxLength={80} required disabled={Boolean(roles.find((item) => item.id === selectedRoleId)?.is_system)} />
          </label>
          {Object.entries(permissionCatalog).map(([groupKey, group]) => (
            <fieldset className="permission-group" key={groupKey}>
              <legend>{group.label}</legend>
              <div className="permission-options">
                {Object.entries(group.permissions).map(([permission, label]) => (
                  <label className="checkbox-row" key={permission}>
                    <input
                      type="checkbox"
                      checked={rolePermissions.includes(permission)}
                      disabled={roles.find((item) => item.id === selectedRoleId)?.name === 'Admin'}
                      onChange={() => toggleRolePermission(permission)}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          <div className="dashboard-actions role-editor-actions">
            {selectedRoleId && !roles.find((item) => item.id === selectedRoleId)?.is_system && (
              <button className="btn-danger" type="button" onClick={() => void removeRole()}>Удалить роль</button>
            )}
            <button className="btn-primary" type="submit" disabled={roles.find((item) => item.id === selectedRoleId)?.name === 'Admin'}>Сохранить роль</button>
          </div>
        </form>
      )}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr><th>Логин</th><th>Роль</th><th>Статус</th><th></th></tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>{isAdmin ? (
                  <select
                    value={user.role}
                    onChange={(event) => void changeUserRole(user.id, event.target.value)}
                    disabled={user.id === currentUser?.id}
                    aria-label={`Роль пользователя ${user.username}`}
                  >
                    {roles.map((item) => <option key={item.id} value={item.name}>{item.name}</option>)}
                  </select>
                ) : user.role}</td>
                <td>{user.is_active ? 'Активен' : 'Заблокирован'}</td>
                <td>
                  <button className="btn-outline" onClick={async () => { await updateUser(user.id, { is_active: !user.is_active }); load(); }}>
                    {user.is_active ? 'Заблокировать' : 'Разблокировать'}
                  </button>
                  <button className="btn-danger" onClick={async () => {
                    if (!window.confirm('Удалить пользователя?')) return;
                    await deleteUser(user.id);
                    load();
                  }}>Удалить</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
