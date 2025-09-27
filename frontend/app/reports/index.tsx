import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const { width } = Dimensions.get('window');

interface DashboardStats {
  sales: {
    total_sales: number;
    sales_this_month: number;
    sales_amount_this_month: number;
    sales_amount_last_month: number;
    sales_growth_percentage: number;
  };
  products: {
    total_products: number;
    low_stock_products: number;
    out_of_stock_products: number;
    top_products: Array<{
      product_name: string;
      quantity_sold: number;
      revenue: number;
    }>;
  };
  debts: {
    total_unsettled_debts: number;
    total_debt_amount: number;
  };
  purchases?: {
    total_purchases: number;
    purchases_this_month: number;
    purchases_amount_this_month: number;
    total_suppliers: number;
  };
}

export default function ReportsScreen() {
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    loadUserData();
    loadDashboardStats();
  }, []);

  const loadUserData = async () => {
    try {
      const userData = await AsyncStorage.getItem('user');
      if (userData) {
        setUser(JSON.parse(userData));
      }
    } catch (error) {
      console.error('Error loading user data:', error);
    }
  };

  const loadDashboardStats = async () => {
    setIsLoading(true);
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/reports/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setDashboardStats(data);
      } else {
        Alert.alert('Erreur', 'Impossible de charger les statistiques');
      }
    } catch (error) {
      console.error('Error loading dashboard stats:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return `${amount.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')} FCFA`;
  };

  const getGrowthColor = (percentage: number) => {
    return percentage >= 0 ? '#28a745' : '#dc3545';
  };

  const getGrowthIcon = (percentage: number) => {
    return percentage >= 0 ? 'trending-up' : 'trending-down';
  };

  const renderStatCard = (title: string, value: string, subtitle?: string, color = '#007bff', icon?: string) => (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <View style={styles.statHeader}>
        <Text style={styles.statTitle}>{title}</Text>
        {icon && <Ionicons name={icon as any} size={24} color={color} />}
      </View>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
      {subtitle && <Text style={styles.statSubtitle}>{subtitle}</Text>}
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
        <Text style={styles.title}>Rapports & Statistiques</Text>
        <TouchableOpacity
          style={styles.refreshButton}
          onPress={loadDashboardStats}
        >
          <Ionicons name="refresh" size={24} color="#007bff" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={loadDashboardStats} />
        }
      >
        {dashboardStats && (
          <>
            {/* Sales Statistics */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>📊 Ventes</Text>
              <View style={styles.statsGrid}>
                {renderStatCard(
                  'Total Ventes',
                  dashboardStats.sales.total_sales.toString(),
                  'Toutes périodes',
                  '#28a745',
                  'receipt-outline'
                )}
                {renderStatCard(
                  'Ventes ce mois',
                  dashboardStats.sales.sales_this_month.toString(),
                  formatCurrency(dashboardStats.sales.sales_amount_this_month),
                  '#007bff',
                  'calendar-outline'
                )}
              </View>

              {/* Growth indicator */}
              <View style={styles.growthCard}>
                <View style={styles.growthHeader}>
                  <Ionicons 
                    name={getGrowthIcon(dashboardStats.sales.sales_growth_percentage)} 
                    size={20} 
                    color={getGrowthColor(dashboardStats.sales.sales_growth_percentage)} 
                  />
                  <Text style={[styles.growthText, { color: getGrowthColor(dashboardStats.sales.sales_growth_percentage) }]}>
                    {dashboardStats.sales.sales_growth_percentage >= 0 ? '+' : ''}
                    {dashboardStats.sales.sales_growth_percentage.toFixed(1)}%
                  </Text>
                </View>
                <Text style={styles.growthLabel}>
                  vs mois dernier ({formatCurrency(dashboardStats.sales.sales_amount_last_month)})
                </Text>
              </View>
            </View>

            {/* Products Statistics */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>📦 Produits</Text>
              <View style={styles.statsGrid}>
                {renderStatCard(
                  'Total Produits',
                  dashboardStats.products.total_products.toString(),
                  'En inventaire',
                  '#6f42c1',
                  'cube-outline'
                )}
                {renderStatCard(
                  'Stock Faible',
                  dashboardStats.products.low_stock_products.toString(),
                  '≤ 5 unités',
                  '#ff9500',
                  'warning-outline'
                )}
                {renderStatCard(
                  'Rupture de Stock',
                  dashboardStats.products.out_of_stock_products.toString(),
                  'À réapprovisionner',
                  '#dc3545',
                  'alert-circle-outline'
                )}
              </View>

              {/* Top Products */}
              {dashboardStats.products.top_products.length > 0 && (
                <View style={styles.topProductsCard}>
                  <Text style={styles.cardTitle}>🏆 Top Produits (ce mois)</Text>
                  {dashboardStats.products.top_products.map((product, index) => (
                    <View key={index} style={styles.topProductItem}>
                      <View style={styles.topProductInfo}>
                        <Text style={styles.topProductName}>{product.product_name}</Text>
                        <Text style={styles.topProductDetails}>
                          {product.quantity_sold} vendus • {formatCurrency(product.revenue)}
                        </Text>
                      </View>
                      <Text style={styles.topProductRank}>#{index + 1}</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>

            {/* Purchases Statistics (Admin/Manager only) */}
            {dashboardStats.purchases && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>🛒 Achats</Text>
                <View style={styles.statsGrid}>
                  {renderStatCard(
                    'Total Achats',
                    dashboardStats.purchases.total_purchases.toString(),
                    'Toutes périodes',
                    '#17a2b8',
                    'bag-outline'
                  )}
                  {renderStatCard(
                    'Achats ce mois',
                    dashboardStats.purchases.purchases_this_month.toString(),
                    formatCurrency(dashboardStats.purchases.purchases_amount_this_month),
                    '#fd7e14',
                    'calendar-outline'
                  )}
                  {renderStatCard(
                    'Fournisseurs',
                    dashboardStats.purchases.total_suppliers.toString(),
                    'Actifs',
                    '#6610f2',
                    'people-outline'
                  )}
                </View>
              </View>
            )}

            {/* Debts Statistics */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>💳 Dettes</Text>
              <View style={styles.statsGrid}>
                {renderStatCard(
                  'Dettes Non Réglées',
                  dashboardStats.debts.total_unsettled_debts.toString(),
                  formatCurrency(dashboardStats.debts.total_debt_amount),
                  '#dc3545',
                  'card-outline'
                )}
              </View>
            </View>

            {/* Quick Actions */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>⚡ Actions Rapides</Text>
              <View style={styles.actionsGrid}>
                <TouchableOpacity
                  style={styles.actionCard}
                  onPress={() => router.push('/reports/sales')}
                >
                  <Ionicons name="bar-chart-outline" size={32} color="#007bff" />
                  <Text style={styles.actionTitle}>Rapport Ventes</Text>
                  <Text style={styles.actionSubtitle}>Détaillé avec filtres</Text>
                </TouchableOpacity>

                {(user?.role === 'admin' || user?.role === 'gérant') && (
                  <TouchableOpacity
                    style={styles.actionCard}
                    onPress={() => router.push('/reports/purchases')}
                  >
                    <Ionicons name="receipt-outline" size={32} color="#17a2b8" />
                    <Text style={styles.actionTitle}>Rapport Achats</Text>
                    <Text style={styles.actionSubtitle}>Par fournisseur & date</Text>
                  </TouchableOpacity>
                )}

                <TouchableOpacity
                  style={styles.actionCard}
                  onPress={() => router.push('/reports/stock')}
                >
                  <Ionicons name="layers-outline" size={32} color="#28a745" />
                  <Text style={styles.actionTitle}>État du Stock</Text>
                  <Text style={styles.actionSubtitle}>Inventaire détaillé</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.actionCard}
                  onPress={() => router.push('/debts')}
                >
                  <Ionicons name="wallet-outline" size={32} color="#dc3545" />
                  <Text style={styles.actionTitle}>Gestion Dettes</Text>
                  <Text style={styles.actionSubtitle}>Suivi des créances</Text>
                </TouchableOpacity>
              </View>
            </View>
          </>
        )}
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
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  statCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    flex: 1,
    minWidth: (width - 56) / 2,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statTitle: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statSubtitle: {
    fontSize: 12,
    color: '#999',
  },
  growthCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginTop: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  growthHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  growthText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  growthLabel: {
    fontSize: 14,
    color: '#666',
  },
  topProductsCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginTop: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  topProductItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  topProductInfo: {
    flex: 1,
  },
  topProductName: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  topProductDetails: {
    fontSize: 12,
    color: '#666',
  },
  topProductRank: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007bff',
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  actionCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    flex: 1,
    minWidth: (width - 56) / 2,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  actionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginTop: 8,
    textAlign: 'center',
  },
  actionSubtitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    textAlign: 'center',
  },
});