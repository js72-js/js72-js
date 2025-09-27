import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface PaymentMethod {
  id: string;
  name: string;
  is_active: boolean;
}

interface Sale {
  id: string;
  sale_number: string;
  total_amount: number;
  status: string;
}

interface PaymentData {
  payment_method_id: string;
  amount: number;
}

export default function PaymentScreen() {
  const { saleId } = useLocalSearchParams();
  const [sale, setSale] = useState<Sale | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [selectedPayments, setSelectedPayments] = useState<{[key: string]: string}>({});
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (saleId) {
      loadData();
    }
  }, [saleId]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadSale(), loadPaymentMethods()]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSale = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/sales/${saleId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSale(data);
      } else {
        Alert.alert('Erreur', 'Impossible de charger la vente');
        router.back();
      }
    } catch (error) {
      console.error('Error loading sale:', error);
      Alert.alert('Erreur', 'Problème de connexion');
      router.back();
    }
  };

  const loadPaymentMethods = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/payment-methods`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPaymentMethods(data);
      }
    } catch (error) {
      console.error('Error loading payment methods:', error);
    }
  };

  const updatePaymentAmount = (methodId: string, amount: string) => {
    setSelectedPayments(prev => ({
      ...prev,
      [methodId]: amount
    }));
  };

  const calculateTotalPayments = () => {
    return Object.values(selectedPayments).reduce((total, amount) => {
      const numAmount = parseFloat(amount) || 0;
      return total + numAmount;
    }, 0);
  };

  const validatePayments = () => {
    const totalPayments = calculateTotalPayments();
    const saleTotal = sale?.total_amount || 0;

    if (totalPayments === 0) {
      Alert.alert('Erreur', 'Veuillez saisir au moins un montant de paiement');
      return false;
    }

    if (totalPayments > saleTotal) {
      Alert.alert('Erreur', 'Le total des paiements ne peut pas dépasser le montant de la vente');
      return false;
    }

    return true;
  };

  const processPayment = async () => {
    if (!validatePayments()) return;

    const totalPayments = calculateTotalPayments();
    const saleTotal = sale?.total_amount || 0;
    const debtAmount = saleTotal - totalPayments;

    // Prepare payment data
    const payments: PaymentData[] = [];
    Object.entries(selectedPayments).forEach(([methodId, amount]) => {
      const numAmount = parseFloat(amount) || 0;
      if (numAmount > 0) {
        payments.push({
          payment_method_id: methodId,
          amount: numAmount
        });
      }
    });

    if (debtAmount > 0) {
      // Show debt confirmation dialog
      Alert.alert(
        'Paiement partiel',
        `Montant restant: ${debtAmount.toFixed(0)} FCFA\n\nVoulez-vous enregistrer cette dette ?`,
        [
          { text: 'Annuler', style: 'cancel' },
          {
            text: 'Enregistrer la dette',
            onPress: () => showDebtForm(payments, debtAmount),
          },
        ]
      );
    } else {
      // Complete payment
      await completeSale(payments);
    }
  };

  const showDebtForm = (payments: PaymentData[], debtAmount: number) => {
    Alert.prompt(
      'Enregistrer une dette',
      'Nom du débiteur:',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Enregistrer',
          onPress: async (debtorName) => {
            if (debtorName?.trim()) {
              await createDebt(debtorName.trim(), debtAmount);
              await completeSale(payments);
            } else {
              Alert.alert('Erreur', 'Le nom du débiteur est requis');
            }
          },
        },
      ],
      'plain-text'
    );
  };

  const createDebt = async (debtorName: string, amount: number) => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const user = await AsyncStorage.getItem('user');
      const userData = user ? JSON.parse(user) : null;

      const response = await fetch(`${BACKEND_URL}/api/sales/${saleId}/debt`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          debtor_name: debtorName,
          seller_name: userData?.name || 'Vendeur',
          amount: amount,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erreur lors de la création de la dette');
      }
    } catch (error) {
      console.error('Error creating debt:', error);
      Alert.alert('Erreur', 'Impossible d\'enregistrer la dette');
      throw error;
    }
  };

  const completeSale = async (payments: PaymentData[]) => {
    setIsLoading(true);
    try {
      const token = await AsyncStorage.getItem('access_token');
      const user = await AsyncStorage.getItem('user');
      const userData = user ? JSON.parse(user) : null;

      const response = await fetch(`${BACKEND_URL}/api/sales/${saleId}/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          payments: payments,
          seller_name: userData?.name || 'Vendeur',
        }),
      });

      const result = await response.json();

      if (response.ok) {
        Alert.alert(
          'Vente finalisée !',
          `Vente #${sale?.sale_number} terminée avec succès\n\nMontant total: ${result.total_amount.toFixed(0)} FCFA\nMontant payé: ${result.paid_amount.toFixed(0)} FCFA${result.debt_amount > 0 ? `\nDette: ${result.debt_amount.toFixed(0)} FCFA` : ''}`,
          [
            {
              text: 'Nouvelle vente',
              onPress: () => router.push('/sales/new'),
            },
            {
              text: 'Dashboard',
              onPress: () => router.push('/dashboard'),
            },
          ]
        );
      } else {
        Alert.alert('Erreur', result.detail || 'Impossible de finaliser la vente');
      }
    } catch (error) {
      console.error('Error completing sale:', error);
      Alert.alert('Erreur', 'Problème de connexion au serveur');
    } finally {
      setIsLoading(false);
    }
  };

  if (!sale) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text>Chargement...</Text>
        </View>
      </SafeAreaView>
    );
  }

  const totalPayments = calculateTotalPayments();
  const remainingAmount = sale.total_amount - totalPayments;

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => router.back()}
          >
            <Ionicons name="arrow-back" size={24} color="#007bff" />
          </TouchableOpacity>
          
          <View style={styles.headerInfo}>
            <Text style={styles.title}>Paiement</Text>
            <Text style={styles.saleNumber}>#{sale.sale_number}</Text>
          </View>
          
          <View style={styles.placeholder} />
        </View>

        <ScrollView style={styles.content}>
          <View style={styles.saleInfo}>
            <Text style={styles.totalLabel}>Total à payer:</Text>
            <Text style={styles.totalAmount}>{sale.total_amount.toFixed(0)} FCFA</Text>
          </View>

          <View style={styles.paymentSection}>
            <Text style={styles.sectionTitle}>Modes de paiement</Text>
            
            {paymentMethods.map(method => (
              <View key={method.id} style={styles.paymentMethod}>
                <Text style={styles.methodName}>{method.name}</Text>
                <TextInput
                  style={styles.amountInput}
                  placeholder="0"
                  placeholderTextColor="#666"
                  keyboardType="numeric"
                  value={selectedPayments[method.id] || ''}
                  onChangeText={(amount) => updatePaymentAmount(method.id, amount)}
                />
              </View>
            ))}
          </View>

          <View style={styles.summary}>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Total des paiements:</Text>
              <Text style={styles.summaryValue}>
                {totalPayments.toFixed(0)} FCFA
              </Text>
            </View>
            
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Montant restant:</Text>
              <Text style={[
                styles.summaryValue,
                remainingAmount > 0 ? styles.debtAmount : styles.completeAmount
              ]}>
                {remainingAmount.toFixed(0)} FCFA
              </Text>
            </View>
          </View>

          {remainingAmount > 0 && (
            <View style={styles.debtNotice}>
              <Ionicons name="warning-outline" size={20} color="#ff9500" />
              <Text style={styles.debtNoticeText}>
                Une dette de {remainingAmount.toFixed(0)} FCFA sera créée
              </Text>
            </View>
          )}
        </ScrollView>

        <View style={styles.footer}>
          <TouchableOpacity
            style={styles.backToCartButton}
            onPress={() => router.back()}
          >
            <Text style={styles.backToCartText}>Retour au panier</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[
              styles.completeButton,
              isLoading && styles.completeButtonDisabled
            ]}
            onPress={processPayment}
            disabled={isLoading || totalPayments === 0}
          >
            <Text style={styles.completeButtonText}>
              {isLoading ? 'Finalisation...' : 'Finaliser la vente'}
            </Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
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
    alignItems: 'center',
    justifyContent: 'center',
  },
  keyboardView: {
    flex: 1,
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
  headerInfo: {
    alignItems: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  saleNumber: {
    fontSize: 14,
    color: '#007bff',
    fontWeight: '600',
  },
  placeholder: {
    width: 40,
  },
  content: {
    flex: 1,
    padding: 16,
  },
  saleInfo: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  totalLabel: {
    fontSize: 16,
    color: '#666',
    marginBottom: 8,
  },
  totalAmount: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#28a745',
  },
  paymentSection: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
  },
  paymentMethod: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  methodName: {
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  amountInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 8,
    width: 120,
    textAlign: 'right',
    fontSize: 16,
    backgroundColor: '#f9f9f9',
  },
  summary: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  summaryLabel: {
    fontSize: 16,
    color: '#333',
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  debtAmount: {
    color: '#dc3545',
  },
  completeAmount: {
    color: '#28a745',
  },
  debtNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff3cd',
    padding: 12,
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#ff9500',
    marginBottom: 16,
  },
  debtNoticeText: {
    fontSize: 14,
    color: '#856404',
    marginLeft: 8,
    flex: 1,
  },
  footer: {
    flexDirection: 'row',
    gap: 12,
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  backToCartButton: {
    flex: 1,
    backgroundColor: '#6c757d',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  backToCartText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  completeButton: {
    flex: 2,
    backgroundColor: '#28a745',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  completeButtonDisabled: {
    backgroundColor: '#ccc',
  },
  completeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});