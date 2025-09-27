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
  FlatList,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Picker } from '@react-native-picker/picker';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Supplier {
  id: string;
  name: string;
}

interface Product {
  id: string;
  name: string;
  code: string;
  image?: string;
  purchase_price: number;
}

interface PurchaseItem {
  product_id: string;
  product_name: string;
  product_code: string;
  product_image?: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
}

export default function AddPurchaseScreen() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [purchaseItems, setPurchaseItems] = useState<PurchaseItem[]>([]);
  const [currentPurchase, setCurrentPurchase] = useState<any>(null);
  
  const [formData, setFormData] = useState({
    supplier_id: '',
    invoice_number: '',
    notes: '',
  });
  
  const [showAddItem, setShowAddItem] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [itemQuantity, setItemQuantity] = useState('1');
  const [itemCost, setItemCost] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadSuppliers(), loadProducts()]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSuppliers = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/suppliers`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSuppliers(data);
      }
    } catch (error) {
      console.error('Error loading suppliers:', error);
    }
  };

  const loadProducts = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/products`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setProducts(data);
      }
    } catch (error) {
      console.error('Error loading products:', error);
    }
  };

  const createPurchase = async () => {
    if (!formData.supplier_id) {
      Alert.alert('Erreur', 'Veuillez sélectionner un fournisseur');
      return;
    }

    if (!formData.invoice_number.trim()) {
      Alert.alert('Erreur', 'Le numéro de facture est requis');
      return;
    }

    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/purchases`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          supplier_id: formData.supplier_id,
          invoice_number: formData.invoice_number.trim(),
          notes: formData.notes.trim() || null,
        }),
      });

      if (response.ok) {
        const purchase = await response.json();
        setCurrentPurchase(purchase);
        Alert.alert('Succès', 'Achat créé. Vous pouvez maintenant ajouter des articles.');
      } else {
        const error = await response.json();
        Alert.alert('Erreur', error.detail || 'Impossible de créer l\'achat');
      }
    } catch (error) {
      console.error('Error creating purchase:', error);
      Alert.alert('Erreur', 'Problème de connexion au serveur');
    }
  };

  const addItemToPurchase = async () => {
    if (!selectedProduct) {
      Alert.alert('Erreur', 'Veuillez sélectionner un produit');
      return;
    }

    if (!itemQuantity || parseInt(itemQuantity) <= 0) {
      Alert.alert('Erreur', 'La quantité doit être supérieure à 0');
      return;
    }

    if (!itemCost || parseFloat(itemCost) <= 0) {
      Alert.alert('Erreur', 'Le coût unitaire doit être supérieur à 0');
      return;
    }

    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/purchases/${currentPurchase.id}/items`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_id: selectedProduct,
          quantity: parseInt(itemQuantity),
          unit_cost: parseFloat(itemCost),
        }),
      });

      if (response.ok) {
        await loadPurchaseItems();
        setSelectedProduct('');
        setItemQuantity('1');
        setItemCost('');
        setShowAddItem(false);
        Alert.alert('Succès', 'Article ajouté à l\'achat');
      } else {
        const error = await response.json();
        Alert.alert('Erreur', error.detail || 'Impossible d\'ajouter l\'article');
      }
    } catch (error) {
      console.error('Error adding item:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    }
  };

  const loadPurchaseItems = async () => {
    if (!currentPurchase) return;

    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/purchases/${currentPurchase.id}/items`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const items = await response.json();
        setPurchaseItems(items.map((item: any) => ({
          product_id: item.product_id,
          product_name: item.product_name,
          product_code: item.product_code,
          product_image: item.product_image,
          quantity: item.quantity,
          unit_cost: item.unit_cost,
          total_cost: item.total_cost,
        })));
      }
    } catch (error) {
      console.error('Error loading purchase items:', error);
    }
  };

  const finalizePurchase = async () => {
    if (purchaseItems.length === 0) {
      Alert.alert('Erreur', 'Veuillez ajouter au moins un article avant de finaliser');
      return;
    }

    Alert.alert(
      'Finaliser l\'achat',
      'Cette action va mettre à jour les stocks des produits. Voulez-vous continuer ?',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Finaliser',
          onPress: async () => {
            try {
              const token = await AsyncStorage.getItem('access_token');
              const response = await fetch(`${BACKEND_URL}/api/purchases/${currentPurchase.id}/finalize`, {
                method: 'POST',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json',
                },
              });

              if (response.ok) {
                Alert.alert(
                  'Achat finalisé !',
                  'L\'achat a été finalisé et les stocks ont été mis à jour.',
                  [
                    {
                      text: 'Retour à la liste',
                      onPress: () => router.back(),
                    },
                  ]
                );
              } else {
                const error = await response.json();
                Alert.alert('Erreur', error.detail || 'Impossible de finaliser l\'achat');
              }
            } catch (error) {
              console.error('Error finalizing purchase:', error);
              Alert.alert('Erreur', 'Problème de connexion');
            }
          },
        },
      ]
    );
  };

  const totalAmount = purchaseItems.reduce((sum, item) => sum + item.total_cost, 0);

  const renderPurchaseItem = ({ item }: { item: PurchaseItem }) => (
    <View style={styles.itemCard}>
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
          <Text style={styles.itemDetails}>
            Qté: {item.quantity} × {item.unit_cost.toFixed(0)} FCFA
          </Text>
        </View>
        <Text style={styles.itemTotal}>{item.total_cost.toFixed(0)} FCFA</Text>
      </View>
    </View>
  );

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
            <Text style={styles.title}>Nouvel Achat</Text>
            {currentPurchase && (
              <Text style={styles.purchaseNumber}>#{currentPurchase.purchase_number}</Text>
            )}
          </View>
          
          <View style={styles.placeholder} />
        </View>

        <ScrollView style={styles.content}>
          {!currentPurchase ? (
            // Purchase creation form
            <View style={styles.formSection}>
              <Text style={styles.sectionTitle}>Informations de l'achat</Text>
              
              <View style={styles.inputContainer}>
                <Text style={styles.label}>Fournisseur *</Text>
                <View style={styles.pickerContainer}>
                  <Picker
                    selectedValue={formData.supplier_id}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, supplier_id: value }))}
                    style={styles.picker}
                  >
                    <Picker.Item label="Sélectionner un fournisseur" value="" />
                    {suppliers.map(supplier => (
                      <Picker.Item 
                        key={supplier.id} 
                        label={supplier.name} 
                        value={supplier.id} 
                      />
                    ))}
                  </Picker>
                </View>
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>Numéro de facture *</Text>
                <TextInput
                  style={styles.input}
                  value={formData.invoice_number}
                  onChangeText={(text) => setFormData(prev => ({ ...prev, invoice_number: text }))}
                  placeholder="Entrez le numéro de facture"
                  placeholderTextColor="#666"
                />
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>Notes (optionnel)</Text>
                <TextInput
                  style={[styles.input, styles.textArea]}
                  value={formData.notes}
                  onChangeText={(text) => setFormData(prev => ({ ...prev, notes: text }))}
                  placeholder="Notes sur l'achat"
                  placeholderTextColor="#666"
                  multiline
                  numberOfLines={3}
                />
              </View>

              <TouchableOpacity
                style={styles.createButton}
                onPress={createPurchase}
              >
                <Text style={styles.createButtonText}>Créer l'achat</Text>
              </TouchableOpacity>
            </View>
          ) : (
            // Purchase items management
            <>
              <View style={styles.purchaseInfo}>
                <Text style={styles.infoTitle}>Achat #{currentPurchase.purchase_number}</Text>
                <Text style={styles.infoDetail}>
                  Fournisseur: {suppliers.find(s => s.id === formData.supplier_id)?.name}
                </Text>
                <Text style={styles.infoDetail}>Facture: {formData.invoice_number}</Text>
              </View>

              <View style={styles.itemsSection}>
                <View style={styles.itemsHeader}>
                  <Text style={styles.sectionTitle}>Articles</Text>
                  <TouchableOpacity
                    style={styles.addItemButton}
                    onPress={() => setShowAddItem(true)}
                  >
                    <Ionicons name="add-circle" size={24} color="#007bff" />
                  </TouchableOpacity>
                </View>

                <FlatList
                  data={purchaseItems}
                  keyExtractor={(item) => item.product_id}
                  renderItem={renderPurchaseItem}
                  ListEmptyComponent={
                    <View style={styles.emptyItems}>
                      <Text style={styles.emptyText}>Aucun article ajouté</Text>
                    </View>
                  }
                />

                {showAddItem && (
                  <View style={styles.addItemForm}>
                    <Text style={styles.formTitle}>Ajouter un article</Text>
                    
                    <View style={styles.inputContainer}>
                      <Text style={styles.label}>Produit</Text>
                      <View style={styles.pickerContainer}>
                        <Picker
                          selectedValue={selectedProduct}
                          onValueChange={setSelectedProduct}
                          style={styles.picker}
                        >
                          <Picker.Item label="Sélectionner un produit" value="" />
                          {products.map(product => (
                            <Picker.Item 
                              key={product.id} 
                              label={`${product.name} (${product.code})`} 
                              value={product.id} 
                            />
                          ))}
                        </Picker>
                      </View>
                    </View>

                    <View style={styles.row}>
                      <View style={styles.halfInput}>
                        <Text style={styles.label}>Quantité</Text>
                        <TextInput
                          style={styles.input}
                          value={itemQuantity}
                          onChangeText={setItemQuantity}
                          keyboardType="numeric"
                          placeholder="1"
                        />
                      </View>

                      <View style={styles.halfInput}>
                        <Text style={styles.label}>Coût unitaire</Text>
                        <TextInput
                          style={styles.input}
                          value={itemCost}
                          onChangeText={setItemCost}
                          keyboardType="numeric"
                          placeholder="0"
                        />
                      </View>
                    </View>

                    <View style={styles.formActions}>
                      <TouchableOpacity
                        style={styles.cancelButton}
                        onPress={() => setShowAddItem(false)}
                      >
                        <Text style={styles.cancelButtonText}>Annuler</Text>
                      </TouchableOpacity>
                      
                      <TouchableOpacity
                        style={styles.addButton}
                        onPress={addItemToPurchase}
                      >
                        <Text style={styles.addButtonText}>Ajouter</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}
              </View>

              {purchaseItems.length > 0 && (
                <View style={styles.totalSection}>
                  <Text style={styles.totalLabel}>Total de l'achat:</Text>
                  <Text style={styles.totalAmount}>{totalAmount.toFixed(0)} FCFA</Text>
                  
                  <TouchableOpacity
                    style={styles.finalizeButton}
                    onPress={finalizePurchase}
                  >
                    <Text style={styles.finalizeButtonText}>Finaliser l'achat</Text>
                  </TouchableOpacity>
                </View>
              )}
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
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
  purchaseNumber: {
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
  formSection: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
  },
  inputContainer: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    backgroundColor: '#fff',
  },
  picker: {
    height: 50,
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  createButton: {
    backgroundColor: '#007bff',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 16,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  purchaseInfo: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  infoDetail: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  itemsSection: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginBottom: 16,
  },
  itemsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  addItemButton: {
    padding: 4,
  },
  itemCard: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  itemHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  itemImage: {
    width: 40,
    height: 40,
    borderRadius: 4,
    marginRight: 12,
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  itemCode: {
    fontSize: 12,
    color: '#666',
  },
  itemDetails: {
    fontSize: 12,
    color: '#666',
  },
  itemTotal: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#28a745',
  },
  emptyItems: {
    padding: 32,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
  },
  addItemForm: {
    padding: 16,
    backgroundColor: '#f8f9fa',
    margin: 16,
    borderRadius: 8,
  },
  formTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  halfInput: {
    flex: 1,
  },
  formActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  cancelButton: {
    flex: 1,
    padding: 12,
    borderRadius: 6,
    backgroundColor: '#6c757d',
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#fff',
    fontWeight: '500',
  },
  addButton: {
    flex: 1,
    padding: 12,
    borderRadius: 6,
    backgroundColor: '#28a745',
    alignItems: 'center',
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '500',
  },
  totalSection: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  totalLabel: {
    fontSize: 16,
    color: '#666',
    marginBottom: 8,
  },
  totalAmount: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#28a745',
    marginBottom: 16,
  },
  finalizeButton: {
    backgroundColor: '#007bff',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 8,
  },
  finalizeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});