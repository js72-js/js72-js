import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import OfflineStorageClass from '../../services/OfflineStorage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface SyncStatus {
  isOnline: boolean;
  pendingCount: number;
  lastSyncTime: Date | null;
  isLoading: boolean;
}

export default function SyncScreen() {
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    isOnline: false,
    pendingCount: 0,
    lastSyncTime: null,
    isLoading: false,
  });

  const [offlineSales, setOfflineSales] = useState<any[]>([]);

  useEffect(() => {
    loadSyncStatus();
    const interval = setInterval(loadSyncStatus, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadSyncStatus = async () => {
    try {
      const networkStatus = OfflineStorageService.getNetworkStatus();
      const pendingCount = await OfflineStorageService.getPendingSyncCount();
      const lastSyncTime = await OfflineStorageService.getLastSyncTime();
      const sales = await OfflineStorageService.getOfflineSales();

      setSyncStatus({
        isOnline: networkStatus.isConnected && networkStatus.isInternetReachable !== false,
        pendingCount,
        lastSyncTime,
        isLoading: false,
      });

      setOfflineSales(sales);
    } catch (error) {
      console.error('Error loading sync status:', error);
    }
  };

  const handleManualSync = async () => {
    if (!syncStatus.isOnline) {
      Alert.alert('Hors ligne', 'Impossible de synchroniser sans connexion internet');
      return;
    }

    if (syncStatus.pendingCount === 0) {
      Alert.alert('Rien à synchroniser', 'Aucune donnée en attente de synchronisation');
      return;
    }

    setSyncStatus(prev => ({ ...prev, isLoading: true }));

    try {
      const token = await AsyncStorage.getItem('access_token');
      if (!token) {
        Alert.alert('Erreur', 'Token d\'authentification non trouvé');
        return;
      }

      if (!BACKEND_URL) {
        Alert.alert('Erreur', 'URL du serveur non configurée');
        return;
      }

      const result = await OfflineStorageService.manualSync(BACKEND_URL, token);
      
      Alert.alert(
        result.uploadSuccess ? 'Synchronisation réussie' : 'Synchronisation partielle',
        result.message
      );

      // Refresh status after sync
      await loadSyncStatus();

    } catch (error) {
      console.error('Manual sync error:', error);
      Alert.alert(
        'Erreur de synchronisation',
        error instanceof Error ? error.message : 'Une erreur est survenue'
      );
    } finally {
      setSyncStatus(prev => ({ ...prev, isLoading: false }));
    }
  };

  const handleClearOfflineData = () => {
    Alert.alert(
      'Effacer les données hors ligne',
      'Cette action supprimera toutes les données non synchronisées. Êtes-vous sûr ?',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Effacer',
          style: 'destructive',
          onPress: async () => {
            try {
              await OfflineStorageService.clearAllOfflineData();
              await loadSyncStatus();
              Alert.alert('Succès', 'Données hors ligne supprimées');
            } catch (error) {
              Alert.alert('Erreur', 'Impossible de supprimer les données');
            }
          },
        },
      ]
    );
  };

  const formatDate = (date: Date) => {
    return date.toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (isOnline: boolean) => {
    return isOnline ? '#28a745' : '#dc3545';
  };

  const getStatusText = (isOnline: boolean) => {
    return isOnline ? 'En ligne' : 'Hors ligne';
  };

  const getStatusIcon = (isOnline: boolean) => {
    return isOnline ? 'wifi' : 'wifi-off';
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Ionicons name="arrow-back" size={24} color="#007bff" />
        </TouchableOpacity>
        <Text style={styles.title}>Synchronisation</Text>
        <TouchableOpacity
          style={styles.refreshButton}
          onPress={loadSyncStatus}
        >
          <Ionicons name="refresh" size={24} color="#007bff" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={syncStatus.isLoading} onRefresh={loadSyncStatus} />
        }
      >
        {/* Network Status */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>État de la connexion</Text>
          <View style={[styles.statusCard, { borderLeftColor: getStatusColor(syncStatus.isOnline) }]}>
            <View style={styles.statusHeader}>
              <Ionicons 
                name={getStatusIcon(syncStatus.isOnline) as any} 
                size={24} 
                color={getStatusColor(syncStatus.isOnline)} 
              />
              <Text style={[styles.statusText, { color: getStatusColor(syncStatus.isOnline) }]}>
                {getStatusText(syncStatus.isOnline)}
              </Text>
            </View>
            <Text style={styles.statusDescription}>
              {syncStatus.isOnline 
                ? 'Connexion internet disponible' 
                : 'Aucune connexion internet - mode hors ligne'
              }
            </Text>
          </View>
        </View>

        {/* Sync Statistics */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Statistiques de synchronisation</Text>
          
          <View style={styles.statsGrid}>
            <View style={[styles.statCard, { borderLeftColor: syncStatus.pendingCount > 0 ? '#ff9500' : '#28a745' }]}>
              <Text style={styles.statValue}>{syncStatus.pendingCount}</Text>
              <Text style={styles.statLabel}>Éléments en attente</Text>
            </View>
            
            <View style={[styles.statCard, { borderLeftColor: '#007bff' }]}>
              <Text style={styles.statValue}>{offlineSales.length}</Text>
              <Text style={styles.statLabel}>Ventes hors ligne</Text>
            </View>
          </View>

          {syncStatus.lastSyncTime && (
            <View style={styles.lastSyncCard}>
              <Text style={styles.lastSyncLabel}>Dernière synchronisation:</Text>
              <Text style={styles.lastSyncTime}>
                {formatDate(syncStatus.lastSyncTime)}
              </Text>
            </View>
          )}
        </View>

        {/* Offline Sales */}
        {offlineSales.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Ventes hors ligne</Text>
            {offlineSales.map((sale, index) => (
              <View key={sale.sync_id} style={styles.offlineSaleCard}>
                <View style={styles.saleHeader}>
                  <Text style={styles.saleNumber}>#{sale.sale_number}</Text>
                  <Text style={styles.saleAmount}>{sale.total_amount.toFixed(0)} FCFA</Text>
                </View>
                <Text style={styles.saleDate}>
                  Créée le: {new Date(sale.created_at).toLocaleString('fr-FR')}
                </Text>
                <Text style={styles.saleItems}>
                  {sale.items.length} article{sale.items.length > 1 ? 's' : ''}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Sync Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Actions</Text>
          
          <TouchableOpacity
            style={[
              styles.actionButton,
              !syncStatus.isOnline && styles.actionButtonDisabled,
              syncStatus.isLoading && styles.actionButtonDisabled
            ]}
            onPress={handleManualSync}
            disabled={!syncStatus.isOnline || syncStatus.isLoading || syncStatus.pendingCount === 0}
          >
            <Ionicons 
              name={syncStatus.isLoading ? "hourglass" : "sync"} 
              size={20} 
              color="#fff" 
            />
            <Text style={styles.actionButtonText}>
              {syncStatus.isLoading ? 'Synchronisation...' : 'Synchroniser maintenant'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionButton, styles.dangerButton]}
            onPress={handleClearOfflineData}
          >
            <Ionicons name="trash" size={20} color="#fff" />
            <Text style={styles.actionButtonText}>
              Effacer les données hors ligne
            </Text>
          </TouchableOpacity>
        </View>

        {/* Information */}
        <View style={styles.section}>
          <View style={styles.infoCard}>
            <Ionicons name="information-circle-outline" size={24} color="#007bff" />
            <View style={styles.infoContent}>
              <Text style={styles.infoTitle}>Fonctionnement hors ligne</Text>
              <Text style={styles.infoText}>
                Les ventes créées sans connexion internet sont automatiquement stockées localement 
                et synchronisées dès que la connexion est rétablie.
              </Text>
            </View>
          </View>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  backButton: {
    padding: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  refreshButton: {
    padding: 8,
  },
  content: {
    flex: 1,
  },
  section: {
    margin: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  statusCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusText: {
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  statusDescription: {
    fontSize: 14,
    color: '#666',
  },
  statsGrid: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  lastSyncCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  lastSyncLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  lastSyncTime: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  offlineSaleCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#ff9500',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  saleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  saleNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  saleAmount: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#28a745',
  },
  saleDate: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  saleItems: {
    fontSize: 12,
    color: '#666',
  },
  actionButton: {
    backgroundColor: '#007bff',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
  },
  actionButtonDisabled: {
    backgroundColor: '#ccc',
  },
  dangerButton: {
    backgroundColor: '#dc3545',
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  infoCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  infoContent: {
    flex: 1,
    marginLeft: 12,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});