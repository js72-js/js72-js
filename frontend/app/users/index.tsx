import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { canManageUsers, getRoleDisplayName, getRoleColor, getAvailableRoles } from '../../utils/roleUtils';
import Constants from 'expo-constants';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function UsersScreen() {
  const { user, token } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [roleModalVisible, setRoleModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const backendUrl = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

  useEffect(() => {
    // Check if user has admin access
    if (!user || !canManageUsers(user.role)) {
      Alert.alert('Accès refusé', 'Vous n\'avez pas les permissions nécessaires pour accéder à cette page.');
      router.back();
      return;
    }
    
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const usersData = await response.json();
        setUsers(usersData);
      } else {
        Alert.alert('Erreur', 'Impossible de charger les utilisateurs');
      }
    } catch (error) {
      console.error('Error loading users:', error);
      Alert.alert('Erreur', 'Erreur de connexion');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadUsers();
  };

  const handleRoleChange = (selectedUser: User) => {
    if (selectedUser.id === user?.id) {
      Alert.alert('Erreur', 'Vous ne pouvez pas modifier votre propre rôle.');
      return;
    }
    setSelectedUser(selectedUser);
    setRoleModalVisible(true);
  };

  const updateUserRole = async (newRole: string) => {
    if (!selectedUser) return;

    try {
      const response = await fetch(`${backendUrl}/api/users/${selectedUser.id}/role`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ role: newRole }),
      });

      if (response.ok) {
        setRoleModalVisible(false);
        setSelectedUser(null);
        Alert.alert('Succès', 'Rôle utilisateur mis à jour');
        loadUsers();
      } else {
        const errorData = await response.json();
        Alert.alert('Erreur', errorData.detail || 'Erreur lors de la mise à jour du rôle');
      }
    } catch (error) {
      console.error('Error updating user role:', error);
      Alert.alert('Erreur', 'Erreur de connexion');
    }
  };

  const deactivateUser = (targetUser: User) => {
    if (targetUser.id === user?.id) {
      Alert.alert('Erreur', 'Vous ne pouvez pas désactiver votre propre compte.');
      return;
    }

    Alert.alert(
      'Confirmation',
      `Êtes-vous sûr de vouloir désactiver l'utilisateur ${targetUser.name}?`,
      [
        {
          text: 'Annuler',
          style: 'cancel',
        },
        {
          text: 'Désactiver',
          style: 'destructive',
          onPress: async () => {
            try {
              const response = await fetch(`${backendUrl}/api/users/${targetUser.id}`, {
                method: 'DELETE',
                headers: {
                  'Authorization': `Bearer ${token}`,
                },
              });

              if (response.ok) {
                Alert.alert('Succès', 'Utilisateur désactivé');
                loadUsers();
              } else {
                const errorData = await response.json();
                Alert.alert('Erreur', errorData.detail || 'Erreur lors de la désactivation');
              }
            } catch (error) {
              console.error('Error deactivating user:', error);
              Alert.alert('Erreur', 'Erreur de connexion');
            }
          },
        },
      ]
    );
  };

  const renderUserItem = ({ item }: { item: User }) => (
    <View style={styles.userCard}>
      <View style={styles.userInfo}>
        <Text style={styles.userName}>{item.name}</Text>
        <Text style={styles.userEmail}>{item.email}</Text>
        <View style={styles.roleContainer}>
          <View style={[styles.roleBadge, { backgroundColor: getRoleColor(item.role) }]}>
            <Text style={styles.roleText}>{getRoleDisplayName(item.role)}</Text>
          </View>
          {!item.is_active && (
            <View style={styles.inactiveBadge}>
              <Text style={styles.inactiveText}>Inactif</Text>
            </View>
          )}
        </View>
      </View>
      <View style={styles.userActions}>
        <TouchableOpacity
          style={[styles.actionButton, styles.changeRoleButton]}
          onPress={() => handleRoleChange(item)}
          disabled={item.id === user?.id}
        >
          <Text style={styles.actionButtonText}>Changer Rôle</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.deactivateButton]}
          onPress={() => deactivateUser(item)}
          disabled={item.id === user?.id || !item.is_active}
        >
          <Text style={styles.actionButtonText}>Désactiver</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderRoleModal = () => (
    <Modal
      animationType="slide"
      transparent={true}
      visible={roleModalVisible}
      onRequestClose={() => setRoleModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Changer le rôle de {selectedUser?.name}</Text>
          
          {getAvailableRoles().map((role) => (
            <TouchableOpacity
              key={role.value}
              style={styles.roleOption}
              onPress={() => updateUserRole(role.value)}
            >
              <View style={[styles.roleOptionBadge, { backgroundColor: getRoleColor(role.value) }]}>
                <Text style={styles.roleOptionText}>{role.label}</Text>
              </View>
              <Text style={styles.roleOptionDescription}>{role.description}</Text>
            </TouchableOpacity>
          ))}
          
          <TouchableOpacity
            style={styles.modalCancelButton}
            onPress={() => setRoleModalVisible(false)}
          >
            <Text style={styles.modalCancelText}>Annuler</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Chargement des utilisateurs...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backButtonText}>← Retour</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Gestion des Utilisateurs</Text>
      </View>

      <FlatList
        data={users}
        keyExtractor={(item) => item.id}
        renderItem={renderUserItem}
        contentContainerStyle={styles.listContainer}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        showsVerticalScrollIndicator={false}
      />

      {renderRoleModal()}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  backButton: {
    marginRight: 16,
  },
  backButtonText: {
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '500',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  listContainer: {
    padding: 16,
  },
  userCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  roleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  roleBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 16,
    marginRight: 8,
  },
  roleText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  inactiveBadge: {
    backgroundColor: '#e74c3c',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
  },
  inactiveText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  userActions: {
    alignItems: 'flex-end',
  },
  actionButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    marginBottom: 4,
    minWidth: 80,
    alignItems: 'center',
  },
  changeRoleButton: {
    backgroundColor: '#3498db',
  },
  deactivateButton: {
    backgroundColor: '#e74c3c',
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#fff',
    margin: 20,
    borderRadius: 20,
    padding: 20,
    alignItems: 'center',
    minWidth: 300,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#333',
  },
  roleOption: {
    width: '100%',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    marginBottom: 12,
    alignItems: 'center',
  },
  roleOptionBadge: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 16,
    marginBottom: 8,
  },
  roleOptionText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  roleOptionDescription: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  modalCancelButton: {
    marginTop: 10,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    backgroundColor: '#95a5a6',
  },
  modalCancelText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});