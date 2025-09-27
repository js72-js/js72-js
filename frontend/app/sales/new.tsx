import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  FlatList,
  TextInput,
  Image,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Product {
  id: string;
  name: string;
  code: string;
  category_id: string;
  selling_price: number;
  stock: number;
  image?: string;
}

interface Category {
  id: string;
  name: string;
}

export default function NewSaleScreen() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [searchText, setSearchText] = useState('');
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentSale, setCurrentSale] = useState<any>(null);

  useEffect(() => {
    loadData();
    createNewSale();
  }, []);

  useEffect(() => {
    filterProducts();
  }, [products, searchText, selectedCategoryId]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadProducts(), loadCategories()]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setIsLoading(false);
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
      } else {
        Alert.alert('Erreur', 'Impossible de charger les produits');
      }
    } catch (error) {
      console.error('Error loading products:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    }
  };

  const loadCategories = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/categories`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCategories(data);
      }
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const createNewSale = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/sales`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const sale = await response.json();
        setCurrentSale(sale);
      } else {
        Alert.alert('Erreur', 'Impossible de créer une nouvelle vente');
      }
    } catch (error) {
      console.error('Error creating sale:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    }
  };

  const filterProducts = () => {
    let filtered = products;

    if (selectedCategoryId) {
      filtered = filtered.filter(product => product.category_id === selectedCategoryId);
    }

    if (searchText) {
      filtered = filtered.filter(product =>
        product.name.toLowerCase().includes(searchText.toLowerCase()) ||
        product.code.toLowerCase().includes(searchText.toLowerCase())
      );
    }

    setFilteredProducts(filtered);
  };

  const getCategoryName = (categoryId: string) => {
    const category = categories.find(cat => cat.id === categoryId);
    return category?.name || 'Non catégorisé';
  };

  const addToCart = async (product: Product) => {
    if (!currentSale) {
      Alert.alert('Erreur', 'Aucune vente en cours');
      return;
    }

    if (product.stock <= 0) {
      Alert.alert('Stock insuffisant', 'Ce produit est en rupture de stock');
      return;
    }

    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/sales/${currentSale.id}/items`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_id: product.id,
          quantity: 1,
        }),
      });

      if (response.ok) {
        Alert.alert('Succès', `${product.name} ajouté au panier`);
      } else {
        const error = await response.json();
        Alert.alert('Erreur', error.detail || 'Impossible d\'ajouter au panier');
      }
    } catch (error) {
      console.error('Error adding to cart:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    }
  };

  const goToCart = () => {
    if (!currentSale) {
      Alert.alert('Erreur', 'Aucune vente en cours');
      return;
    }
    
    router.push({
      pathname: '/sales/cart',
      params: { saleId: currentSale.id }
    });
  };

  const renderProduct = ({ item }: { item: Product }) => (
    <View style={styles.productCard}>
      <View style={styles.productHeader}>
        {item.image && (
          <Image 
            source={{ uri: `data:image/jpeg;base64,${item.image}` }} 
            style={styles.productImage}
          />
        )}
        <View style={styles.productInfo}>
          <Text style={styles.productName}>{item.name}</Text>
          <Text style={styles.productCode}>Code: {item.code}</Text>
          <Text style={styles.productCategory}>
            {getCategoryName(item.category_id)}
          </Text>
          <Text style={styles.productPrice}>
            {item.selling_price.toFixed(0)} FCFA
          </Text>
          <View style={styles.stockContainer}>
            <Text style={[
              styles.stockText,
              { color: item.stock > 0 ? '#28a745' : '#dc3545' }
            ]}>
              Stock: {item.stock}
            </Text>
            {item.stock === 0 && (
              <Text style={styles.outOfStock}>Rupture</Text>
            )}
          </View>
        </View>
      </View>
      
      <TouchableOpacity
        style={[
          styles.addButton,
          item.stock <= 0 && styles.addButtonDisabled
        ]}
        onPress={() => addToCart(item)}
        disabled={item.stock <= 0}
      >
        <Ionicons 
          name="add-circle" 
          size={20} 
          color={item.stock > 0 ? "#fff" : "#ccc"} 
        />
        <Text style={[
          styles.addButtonText,
          item.stock <= 0 && styles.addButtonTextDisabled
        ]}>
          Ajouter
        </Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => router.back()}
          >
            <Ionicons name="arrow-back" size={24} color="#007bff" />
          </TouchableOpacity>
          
          <View style={styles.saleInfo}>
            <Text style={styles.title}>Nouvelle Vente</Text>
            {currentSale && (
              <Text style={styles.saleNumber}>#{currentSale.sale_number}</Text>
            )}
          </View>
          
          <TouchableOpacity
            style={styles.cartButton}
            onPress={goToCart}
          >
            <Ionicons name="basket" size={24} color="#fff" />
          </TouchableOpacity>
        </View>

        <TextInput
          style={styles.searchInput}
          placeholder="Rechercher un produit..."
          value={searchText}
          onChangeText={setSearchText}
          placeholderTextColor="#666"
        />

        <View style={styles.filterContainer}>
          <TouchableOpacity
            style={[
              styles.filterChip,
              selectedCategoryId === '' && styles.filterChipActive
            ]}
            onPress={() => setSelectedCategoryId('')}
          >
            <Text style={[
              styles.filterChipText,
              selectedCategoryId === '' && styles.filterChipTextActive
            ]}>
              Toutes
            </Text>
          </TouchableOpacity>
          
          {categories.map(category => (
            <TouchableOpacity
              key={category.id}
              style={[
                styles.filterChip,
                selectedCategoryId === category.id && styles.filterChipActive
              ]}
              onPress={() => setSelectedCategoryId(category.id)}
            >
              <Text style={[
                styles.filterChipText,
                selectedCategoryId === category.id && styles.filterChipTextActive
              ]}>
                {category.name}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <FlatList
        data={filteredProducts}
        keyExtractor={(item) => item.id}
        renderItem={renderProduct}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={loadData} />
        }
        contentContainerStyle={styles.listContainer}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="storefront-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>
              {products.length === 0 
                ? 'Aucun produit disponible' 
                : 'Aucun produit ne correspond aux filtres'
              }
            </Text>
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
    backgroundColor: '#fff',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  backButton: {
    padding: 8,
  },
  saleInfo: {
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
    marginTop: 2,
  },
  cartButton: {
    backgroundColor: '#007bff',
    borderRadius: 20,
    padding: 8,
  },
  searchInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#f9f9f9',
    color: '#333',
    marginBottom: 16,
  },
  filterContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  filterChip: {
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  filterChipActive: {
    backgroundColor: '#007bff',
  },
  filterChipText: {
    fontSize: 14,
    color: '#666',
  },
  filterChipTextActive: {
    color: '#fff',
    fontWeight: '500',
  },
  listContainer: {
    padding: 16,
    paddingBottom: 80,
  },
  productCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  productHeader: {
    flexDirection: 'row',
    flex: 1,
  },
  productImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
    marginRight: 12,
    backgroundColor: '#f0f0f0',
  },
  productInfo: {
    flex: 1,
  },
  productName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 2,
  },
  productCode: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  productCategory: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  productPrice: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007bff',
    marginBottom: 4,
  },
  stockContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stockText: {
    fontSize: 12,
    fontWeight: '500',
  },
  outOfStock: {
    fontSize: 10,
    color: '#dc3545',
    marginLeft: 8,
    backgroundColor: '#ffebee',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#28a745',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 4,
  },
  addButtonDisabled: {
    backgroundColor: '#f0f0f0',
  },
  addButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
  },
  addButtonTextDisabled: {
    color: '#ccc',
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
    textAlign: 'center',
  },
});