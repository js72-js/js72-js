// Role constants matching backend
export const UserRole = {
  ADMIN: 'admin',
  MANAGER: 'gérant',
  SERVER: 'serveur'
} as const;

export type UserRoleType = typeof UserRole[keyof typeof UserRole];

// Role checking functions
export const hasAdminAccess = (role: string): boolean => {
  return role === UserRole.ADMIN;
};

export const hasManagerAccess = (role: string): boolean => {
  return role === UserRole.ADMIN || role === UserRole.MANAGER;
};

export const hasAnyAccess = (role: string): boolean => {
  return role === UserRole.ADMIN || role === UserRole.MANAGER || role === UserRole.SERVER;
};

export const canAccessPurchases = (role: string): boolean => {
  return role === UserRole.ADMIN || role === UserRole.MANAGER;
};

export const canAccessReports = (role: string): boolean => {
  return hasAnyAccess(role);
};

export const canManageUsers = (role: string): boolean => {
  return role === UserRole.ADMIN;
};

// Role display functions
export const getRoleDisplayName = (role: string): string => {
  switch (role) {
    case UserRole.ADMIN:
      return 'Administrateur';
    case UserRole.MANAGER:
      return 'Gérant';
    case UserRole.SERVER:
      return 'Serveur';
    default:
      return 'Inconnu';
  }
};

export const getRoleDescription = (role: string): string => {
  switch (role) {
    case UserRole.ADMIN:
      return 'Accès complet à toutes les fonctionnalités';
    case UserRole.MANAGER:
      return 'Accès aux ventes et achats';
    case UserRole.SERVER:
      return 'Accès aux ventes uniquement';
    default:
      return 'Rôle inconnu';
  }
};

export const getRoleColor = (role: string): string => {
  switch (role) {
    case UserRole.ADMIN:
      return '#e74c3c'; // Red
    case UserRole.MANAGER:
      return '#f39c12'; // Orange
    case UserRole.SERVER:
      return '#27ae60'; // Green
    default:
      return '#95a5a6'; // Gray
  }
};

// Available roles for role selection
export const getAvailableRoles = () => [
  {
    value: UserRole.ADMIN,
    label: getRoleDisplayName(UserRole.ADMIN),
    description: getRoleDescription(UserRole.ADMIN)
  },
  {
    value: UserRole.MANAGER,
    label: getRoleDisplayName(UserRole.MANAGER),
    description: getRoleDescription(UserRole.MANAGER)
  },
  {
    value: UserRole.SERVER,
    label: getRoleDisplayName(UserRole.SERVER),
    description: getRoleDescription(UserRole.SERVER)
  }
];