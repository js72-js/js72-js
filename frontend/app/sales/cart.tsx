import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  FlatList,
  Image,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface CartItem {
  id: string;
  sale_id: string;
  product_id: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  product_name: string;
  product_code: string;
  product_image?: string;
  available_stock: number;
}

interface Sale {
  id: string;
  sale_number: string;
  total_amount: number;
  status: string;
}

export default function CartScreen() {
  const { saleId } = useLocalSearchParams();
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [sale, setSale] = useState<Sale | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (saleId) {
      loadCartData();
    }
  }, [saleId]);

  const loadCartData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadCartItems(), loadSale()]);
    } catch (error) {
      console.error('Error loading cart data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadCartItems = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/sales/${saleId}/items`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCartItems(data);
      } else {
        Alert.alert('Erreur', 'Impossible de charger le panier');
      }
    } catch (error) {
      console.error('Error loading cart items:', error);
      Alert.alert('Erreur', 'Problème de connexion');
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
      }
    } catch (error) {
      console.error('Error loading sale:', error);
    }
  };

  const updateQuantity = async (itemId: string, newQuantity: number) => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/sales/${saleId}/items/${itemId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ quantity: newQuantity }),
      });

      if (response.ok) {
        await loadCartData(); // Refresh cart
      } else {
        const error = await response.json();
        Alert.alert('Erreur', error.detail || 'Impossible de modifier la quantité');
      }
    } catch (error) {
      console.error('Error updating quantity:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    }
  };

  const removeItem = async (itemId: string) => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/sales/${saleId}/items/${itemId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        await loadCartData(); // Refresh cart
      } else {
        Alert.alert('Erreur', 'Impossible de supprimer l\'article');
      }
    } catch (error) {
      console.error('Error removing item:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    }
  };

  const putOnHold = async () => {
    Alert.alert(
      'Mettre en attente',
      'Voulez-vous mettre cette vente en attente ?',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Confirmer',
          onPress: async () => {
            try {
              const token = await AsyncStorage.getItem('access_token');
              const response = await fetch(`${BACKEND_URL}/api/sales/${saleId}/status`, {
                method: 'PATCH',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: 'on_hold' }),
              });

              if (response.ok) {
                Alert.alert('Succès', 'Vente mise en attente', [
                  {
                    text: 'OK',
                    onPress: () => router.push('/sales/new'),
                  },
                ]);
              } else {
                Alert.alert('Erreur', 'Impossible de mettre en attente');
              }
            } catch (error) {
              console.error('Error putting on hold:', error);
              Alert.alert('Erreur', 'Problème de connexion');
            }
          },
        },
      ]
    );
  };

  const proceedToPayment = () => {
    if (cartItems.length === 0) {
      Alert.alert('Panier vide', 'Ajoutez des produits avant de procéder au paiement');
      return;
    }

    router.push({
      pathname: '/sales/payment',
      params: { saleId: saleId as string }
    });
  };

  const renderCartItem = ({ item }: { item: CartItem }) => (
    <View style={styles.cartItem}>
      <View style={styles.itemHeader}>
        {item.product_image && (
          <Image 
            source={{ uri: `data:image/jpeg;base64,${item.product_image}` }} 
            style={styles.itemImage}
          />
        )}
        <View style={styles.itemInfo}>
          <Text style={styles.itemName}>{item.product_name}</Text>
          <Text style={styles.itemCode}>Code: {item.product_code}</Text>
          <Text style={styles.itemPrice}>
            {item.unit_price.toFixed(0)} FCFA / unité
          </Text>
          <Text style={styles.itemStock}>
            Stock disponible: {item.available_stock}
          </Text>
        </View>
      </View>

      <View style={styles.quantityContainer}>
        <TouchableOpacity
          style={styles.quantityButton}
          onPress={() => updateQuantity(item.id, item.quantity - 1)}
        >
          <Ionicons name="remove" size={16} color="#007bff" />
        </TouchableOpacity>
        
        <Text style={styles.quantityText}>{item.quantity}</Text>
        
        <TouchableOpacity
          style={[
            styles.quantityButton,
            item.quantity >= item.available_stock && styles.quantityButtonDisabled
          ]}
          onPress={() => updateQuantity(item.id, item.quantity + 1)}
          disabled={item.quantity >= item.available_stock}
        >
          <Ionicons 
            name="add" 
            size={16} 
            color={item.quantity >= item.available_stock ? "#ccc" : "#007bff"} 
          />
        </TouchableOpacity>
      </View>

      <View style={styles.itemFooter}>
        <Text style={styles.itemTotal}>
          Total: {item.total_price.toFixed(0)} FCFA
        </Text>
        <TouchableOpacity
          style={styles.removeButton}
          onPress={() => removeItem(item.id)}
        >
          <Ionicons name="trash-outline" size={16} color="#dc3545" />
        </TouchableOpacity>
      </View>
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
        
        <View style={styles.headerInfo}>
          <Text style={styles.title}>Panier</Text>
          {sale && (
            <Text style={styles.saleNumber}>#{sale.sale_number}</Text>
          )}
        </View>
        
        <TouchableOpacity
          style={styles.holdButton}
          onPress={putOnHold}
        >
          <Ionicons name="pause-circle-outline" size={24} color="#ff9500" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={cartItems}
        keyExtractor={(item) => item.id}
        renderItem={renderCartItem}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={loadCartData} />
        }
        contentContainerStyle={styles.listContainer}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="basket-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Votre panier est vide</Text>
            <TouchableOpacity
              style={styles.continueShoppingButton}
              onPress={() => router.back()}
            >
              <Text style={styles.continueShoppingText}>
                Continuer les achats
              </Text>
            </TouchableOpacity>
          </View>
        }
      />

      {cartItems.length > 0 && (
        <View style={styles.footer}>
          <View style={styles.totalContainer}>
            <Text style={styles.totalLabel}>Total de la vente:</Text>
            <Text style={styles.totalAmount}>
              {sale ? sale.total_amount.toFixed(0) : '0'} FCFA
            </Text>
          </View>
          
          <View style={styles.actionButtons}>
            <TouchableOpacity
              style={styles.holdActionButton}
              onPress={putOnHold}
            >
              <Text style={styles.holdActionText}>Mettre en attente</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.paymentButton}
              onPress={proceedToPayment}
            >
              <Text style={styles.paymentButtonText}>Procéder au paiement</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
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
  holdButton: {
    padding: 8,
  },
  listContainer: {
    padding: 16,
    paddingBottom: 200,
  },
  cartItem: {
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
  itemHeader: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  itemImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
    marginRight: 12,
    backgroundColor: '#f0f0f0',
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 2,
  },
  itemCode: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  itemPrice: {
    fontSize: 14,
    color: '#007bff',
    fontWeight: '500',
    marginBottom: 2,
  },
  itemStock: {
    fontSize: 12,
    color: '#666',
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  quantityButton: {
    backgroundColor: '#f0f8ff',
    borderRadius: 20,
    padding: 8,
    marginHorizontal: 8,
  },
  quantityButtonDisabled: {
    backgroundColor: '#f5f5f5',
  },
  quantityText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    minWidth: 40,
    textAlign: 'center',
  },
  itemFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  itemTotal: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#28a745',
  },
  removeButton: {
    backgroundColor: '#ffebee',
    borderRadius: 20,
    padding: 8,
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
    marginBottom: 24,
  },
  continueShoppingButton: {
    backgroundColor: '#007bff',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  continueShoppingText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  totalContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  totalAmount: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#28a745',
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  holdActionButton: {
    flex: 1,
    backgroundColor: '#ff9500',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  holdActionText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  paymentButton: {
    flex: 2,
    backgroundColor: '#28a745',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  paymentButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});