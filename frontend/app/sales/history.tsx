import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  FlatList,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface SaleHistory {
  id: string;
  sale_number: string;
  total_amount: number;
  payment_status: string;
  completed_at: string;
  items_count: number;
  payment_methods: Array<{
    method_name: string;
    amount: number;
  }>;
}

export default function SalesHistoryScreen() {
  const [salesHistory, setSalesHistory] = useState<SaleHistory[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadSalesHistory();
  }, []);

  const loadSalesHistory = async () => {
    setIsLoading(true);
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/sales/history?limit=50`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSalesHistory(data);
      } else {
        Alert.alert('Erreur', 'Impossible de charger l\'historique des ventes');
      }
    } catch (error) {
      console.error('Error loading sales history:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getPaymentStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return '#28a745';
      case 'partial':
        return '#ff9500';
      default:
        return '#666';
    }
  };

  const getPaymentStatusText = (status: string) => {
    switch (status) {
      case 'paid':
        return 'Payé';
      case 'partial':
        return 'Partiel';
      default:
        return status;
    }
  };

  const renderSale = ({ item }: { item: SaleHistory }) => (
    <View style={styles.saleCard}>
      <View style={styles.saleHeader}>
        <View style={styles.saleInfo}>
          <Text style={styles.saleNumber}>#{item.sale_number}</Text>
          <Text style={styles.saleDate}>{formatDate(item.completed_at)}</Text>
          <Text style={styles.itemsCount}>
            {item.items_count} article{item.items_count > 1 ? 's' : ''}
          </Text>
        </View>
        
        <View style={styles.saleAmount}>
          <Text style={styles.amount}>{item.total_amount.toFixed(0)} FCFA</Text>
          <View style={[
            styles.statusBadge,
            { backgroundColor: getPaymentStatusColor(item.payment_status) }
          ]}>
            <Text style={styles.statusText}>
              {getPaymentStatusText(item.payment_status)}
            </Text>
          </View>
        </View>
      </View>
      
      {item.payment_methods.length > 0 && (
        <View style={styles.paymentMethods}>
          <Text style={styles.paymentLabel}>Paiements:</Text>
          {item.payment_methods.map((method, index) => (
            <View key={index} style={styles.paymentMethod}>
              <Text style={styles.methodName}>{method.method_name}</Text>
              <Text style={styles.methodAmount}>
                {method.amount.toFixed(0)} FCFA
              </Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Ionicons name="arrow-back" size={24} color="#007bff" />
        </TouchableOpacity>
        <Text style={styles.title}>Historique des Ventes</Text>
        <TouchableOpacity
          style={styles.refreshButton}
          onPress={loadSalesHistory}
        >
          <Ionicons name="refresh" size={24} color="#007bff" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={salesHistory}
        keyExtractor={(item) => item.id}
        renderItem={renderSale}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={loadSalesHistory} />
        }
        contentContainerStyle={styles.listContainer}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="receipt-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Aucune vente trouvée</Text>
          </View>
        }
      />
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
  listContainer: {
    padding: 16,
  },
  saleCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  saleHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  saleInfo: {
    flex: 1,
  },
  saleNumber: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  saleDate: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  itemsCount: {
    fontSize: 12,
    color: '#999',
  },
  saleAmount: {
    alignItems: 'flex-end',
  },
  amount: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#28a745',
    marginBottom: 8,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    color: '#fff',
    fontWeight: '600',
  },
  paymentMethods: {
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    paddingTop: 12,
  },
  paymentLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
    marginBottom: 8,
  },
  paymentMethod: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  methodName: {
    fontSize: 14,
    color: '#666',
  },
  methodAmount: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    marginTop: 16,
  },
});