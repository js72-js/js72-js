import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { 
  canAccessPurchases, 
  canManageUsers, 
  getRoleDisplayName, 
  getRoleColor 
} from '../../utils/roleUtils';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

export default function DashboardScreen() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    loadUserData();
    initializeApp();
  }, []);

  const loadUserData = async () => {
    try {
      const userData = await AsyncStorage.getItem('user');
      if (userData) {
        setUser(JSON.parse(userData));
      } else {
        router.replace('/auth/login');
      }
    } catch (error) {
      console.error('Error loading user data:', error);
      router.replace('/auth/login');
    }
  };

  const initializeApp = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${process.env.EXPO_PUBLIC_BACKEND_URL}/api/setup/init`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        console.log('App initialized successfully');
      }
    } catch (error) {
      console.error('Initialization error:', error);
    }
  };

  const handleLogout = async () => {
    Alert.alert(
      'Déconnexion',
      'Êtes-vous sûr de vouloir vous déconnecter ?',
      [
        {
          text: 'Annuler',
          style: 'cancel',
        },
        {
          text: 'Déconnexion',
          style: 'destructive',
          onPress: async () => {
            await AsyncStorage.clear();
            router.replace('/auth/login');
          },
        },
      ]
    );
  };

  const canAccessProducts = () => {
    return canAccessPurchases(user?.role || '');
  };

  const canAccessSales = () => {
    return true; // Tous les rôles peuvent accéder aux ventes
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView}>
        <View style={styles.header}>
          <Text style={styles.welcomeText}>
            Bonjour, {user?.name || 'Utilisateur'}
          </Text>
          <View style={styles.roleContainer}>
            <View style={[styles.roleBadge, { backgroundColor: getRoleColor(user?.role || '') }]}>
              <Text style={styles.roleText}>
                {getRoleDisplayName(user?.role || '')}
              </Text>
            </View>
          </View>
          <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
            <Ionicons name="log-out-outline" size={20} color="#fff" />
            <Text style={styles.logoutText}>Déconnexion</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.menuContainer}>
          <Text style={styles.menuTitle}>Menu Principal</Text>

          {canAccessSales() && (
            <>
              <TouchableOpacity
                style={styles.menuItem}
                onPress={() => router.push('/sales/new')}
              >
                <View style={styles.menuItemContent}>
                  <Ionicons name="add-circle-outline" size={24} color="#007bff" />
                  <Text style={styles.menuItemText}>Nouvelle Vente</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color="#666" />
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.menuItem}
                onPress={() => router.push('/sales/pending')}
              >
                <View style={styles.menuItemContent}>
                  <Ionicons name="time-outline" size={24} color="#ff9500" />
                  <Text style={styles.menuItemText}>Ventes en Attente</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color="#666" />
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.menuItem}
                onPress={() => router.push('/sales/history')}
              >
                <View style={styles.menuItemContent}>
                  <Ionicons name="receipt-outline" size={24} color="#28a745" />
                  <Text style={styles.menuItemText}>Historique des Ventes</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color="#666" />
              </TouchableOpacity>
            </>
          )}

          {canAccessProducts() && (
            <>
              <TouchableOpacity
                style={styles.menuItem}
                onPress={() => router.push('/products')}
              >
                <View style={styles.menuItemContent}>
                  <Ionicons name="cube-outline" size={24} color="#6f42c1" />
                  <Text style={styles.menuItemText}>Gestion des Produits</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color="#666" />
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.menuItem}
                onPress={() => router.push('/categories')}
              >
                <View style={styles.menuItemContent}>
                  <Ionicons name="grid-outline" size={24} color="#17a2b8" />
                  <Text style={styles.menuItemText}>Catégories</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color="#666" />
              </TouchableOpacity>
            </>
          )}

          {canAccessPurchases(user?.role || '') && (
            <TouchableOpacity
              style={styles.menuItem}
              onPress={() => router.push('/purchases')}
            >
              <View style={styles.menuItemContent}>
                <Ionicons name="bag-add-outline" size={24} color="#fd7e14" />
                <Text style={styles.menuItemText}>Gestion des Achats</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#666" />
            </TouchableOpacity>
          )}

          {canManageUsers(user?.role || '') && (
            <TouchableOpacity
              style={styles.menuItem}
              onPress={() => router.push('/users')}
            >
              <View style={styles.menuItemContent}>
                <Ionicons name="people-outline" size={24} color="#dc3545" />
                <Text style={styles.menuItemText}>Gestion des Utilisateurs</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#666" />
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => router.push('/reports')}
          >
            <View style={styles.menuItemContent}>
              <Ionicons name="bar-chart-outline" size={24} color="#e83e8c" />
              <Text style={styles.menuItemText}>Rapports & Statistiques</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => router.push('/sync')}
          >
            <View style={styles.menuItemContent}>
              <Ionicons name="sync-outline" size={24} color="#20c997" />
              <Text style={styles.menuItemText}>Synchronisation</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollView: {
    flex: 1,
  },
  header: {
    backgroundColor: '#007bff',
    padding: 24,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
    marginBottom: 24,
  },
  welcomeText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  roleContainer: {
    marginBottom: 16,
  },
  roleBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    alignSelf: 'flex-start',
  },
  roleText: {
    fontSize: 14,
    color: '#fff',
    fontWeight: 'bold',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    alignSelf: 'flex-start',
  },
  logoutText: {
    color: '#fff',
    marginLeft: 8,
    fontSize: 14,
    fontWeight: '500',
  },
  menuContainer: {
    paddingHorizontal: 16,
  },
  menuTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
  },
  menuItem: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  menuItemContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  menuItemText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
    marginLeft: 12,
  },
});