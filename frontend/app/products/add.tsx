import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  Image,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { Picker } from '@react-native-picker/picker';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Category {
  id: string;
  name: string;
  description?: string;
}

export default function AddProductScreen() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    category_id: '',
    purchase_price: '',
    selling_price: '',
    stock: '',
    image: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [imageUri, setImageUri] = useState<string>('');

  useEffect(() => {
    loadCategories();
    requestPermissions();
  }, []);

  const requestPermissions = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission requise', 'Permission d\'accès à la galerie nécessaire');
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
      } else {
        Alert.alert('Erreur', 'Impossible de charger les catégories');
      }
    } catch (error) {
      console.error('Error loading categories:', error);
      Alert.alert('Erreur', 'Problème de connexion');
    }
  };

  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.5,
        base64: true,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        setImageUri(asset.uri || '');
        setFormData(prev => ({
          ...prev,
          image: asset.base64 || ''
        }));
      }
    } catch (error) {
      console.error('Error picking image:', error);
      Alert.alert('Erreur', 'Impossible de sélectionner l\'image');
    }
  };

  const takePhoto = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission requise', 'Permission d\'accès à la caméra nécessaire');
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.5,
        base64: true,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        setImageUri(asset.uri || '');
        setFormData(prev => ({
          ...prev,
          image: asset.base64 || ''
        }));
      }
    } catch (error) {
      console.error('Error taking photo:', error);
      Alert.alert('Erreur', 'Impossible de prendre la photo');
    }
  };

  const showImageOptions = () => {
    Alert.alert(
      'Ajouter une image',
      'Choisir une option',
      [
        {
          text: 'Caméra',
          onPress: takePhoto,
        },
        {
          text: 'Galerie',
          onPress: pickImage,
        },
        {
          text: 'Annuler',
          style: 'cancel',
        },
      ]
    );
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      Alert.alert('Erreur', 'Le nom du produit est requis');
      return false;
    }
    if (!formData.code.trim()) {
      Alert.alert('Erreur', 'Le code du produit est requis');
      return false;
    }
    if (!formData.category_id) {
      Alert.alert('Erreur', 'Veuillez sélectionner une catégorie');
      return false;
    }
    if (!formData.purchase_price || parseFloat(formData.purchase_price) <= 0) {
      Alert.alert('Erreur', 'Le prix d\'achat doit être supérieur à 0');
      return false;
    }
    if (!formData.selling_price || parseFloat(formData.selling_price) <= 0) {
      Alert.alert('Erreur', 'Le prix de vente doit être supérieur à 0');
      return false;
    }
    if (parseFloat(formData.selling_price) < parseFloat(formData.purchase_price)) {
      Alert.alert('Erreur', 'Le prix de vente doit être supérieur ou égal au prix d\'achat');
      return false;
    }
    if (!formData.stock || parseInt(formData.stock) < 0) {
      Alert.alert('Erreur', 'Le stock doit être supérieur ou égal à 0');
      return false;
    }
    return true;
  };

  const handleSave = async () => {
    if (!validateForm()) return;

    setIsLoading(true);

    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BACKEND_URL}/api/products`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name.trim(),
          code: formData.code.trim(),
          category_id: formData.category_id,
          purchase_price: parseFloat(formData.purchase_price),
          selling_price: parseFloat(formData.selling_price),
          stock: parseInt(formData.stock),
          image: formData.image,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        Alert.alert('Succès', 'Produit ajouté avec succès!', [
          {
            text: 'OK',
            onPress: () => router.back(),
          },
        ]);
      } else {
        Alert.alert('Erreur', data.detail || 'Impossible d\'ajouter le produit');
      }
    } catch (error) {
      console.error('Error saving product:', error);
      Alert.alert('Erreur', 'Problème de connexion au serveur');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView style={styles.scrollView}>
          <View style={styles.header}>
            <TouchableOpacity
              style={styles.backButton}
              onPress={() => router.back()}
            >
              <Ionicons name="arrow-back" size={24} color="#007bff" />
            </TouchableOpacity>
            <Text style={styles.title}>Ajouter un Produit</Text>
            <View style={styles.placeholder} />
          </View>

          <View style={styles.form}>
            {/* Image Section */}
            <View style={styles.imageSection}>
              <Text style={styles.label}>Image du produit</Text>
              <TouchableOpacity
                style={styles.imageContainer}
                onPress={showImageOptions}
              >
                {imageUri ? (
                  <Image source={{ uri: imageUri }} style={styles.productImage} />
                ) : (
                  <View style={styles.imagePlaceholder}>
                    <Ionicons name="camera-outline" size={40} color="#666" />
                    <Text style={styles.imagePlaceholderText}>Ajouter une image</Text>
                  </View>
                )}
              </TouchableOpacity>
            </View>

            {/* Form Fields */}
            <View style={styles.inputContainer}>
              <Text style={styles.label}>Nom du produit *</Text>
              <TextInput
                style={styles.input}
                value={formData.name}
                onChangeText={(text) => setFormData(prev => ({ ...prev, name: text }))}
                placeholder="Entrez le nom du produit"
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Code du produit *</Text>
              <TextInput
                style={styles.input}
                value={formData.code}
                onChangeText={(text) => setFormData(prev => ({ ...prev, code: text }))}
                placeholder="Entrez le code du produit"
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Catégorie *</Text>
              <View style={styles.pickerContainer}>
                <Picker
                  selectedValue={formData.category_id}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, category_id: value }))}
                  style={styles.picker}
                >
                  <Picker.Item label="Sélectionner une catégorie" value="" />
                  {categories.map(category => (
                    <Picker.Item 
                      key={category.id} 
                      label={category.name} 
                      value={category.id} 
                    />
                  ))}
                </Picker>
              </View>
            </View>

            <View style={styles.row}>
              <View style={styles.halfInput}>
                <Text style={styles.label}>Prix d'achat *</Text>
                <TextInput
                  style={styles.input}
                  value={formData.purchase_price}
                  onChangeText={(text) => setFormData(prev => ({ ...prev, purchase_price: text }))}
                  placeholder="0"
                  placeholderTextColor="#666"
                  keyboardType="numeric"
                />
              </View>

              <View style={styles.halfInput}>
                <Text style={styles.label}>Prix de vente *</Text>
                <TextInput
                  style={styles.input}
                  value={formData.selling_price}
                  onChangeText={(text) => setFormData(prev => ({ ...prev, selling_price: text }))}
                  placeholder="0"
                  placeholderTextColor="#666"
                  keyboardType="numeric"
                />
              </View>
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Stock initial *</Text>
              <TextInput
                style={styles.input}
                value={formData.stock}
                onChangeText={(text) => setFormData(prev => ({ ...prev, stock: text }))}
                placeholder="0"
                placeholderTextColor="#666"
                keyboardType="numeric"
              />
            </View>

            <TouchableOpacity
              style={[styles.saveButton, isLoading && styles.saveButtonDisabled]}
              onPress={handleSave}
              disabled={isLoading}
            >
              <Text style={styles.saveButtonText}>
                {isLoading ? 'Ajout en cours...' : 'Ajouter le Produit'}
              </Text>
            </TouchableOpacity>
          </View>
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
  scrollView: {
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
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  placeholder: {
    width: 40,
  },
  form: {
    padding: 16,
  },
  imageSection: {
    marginBottom: 24,
  },
  imageContainer: {
    alignItems: 'center',
    marginTop: 8,
  },
  productImage: {
    width: 120,
    height: 120,
    borderRadius: 8,
  },
  imagePlaceholder: {
    width: 120,
    height: 120,
    backgroundColor: '#f0f0f0',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#ddd',
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
  },
  imagePlaceholderText: {
    color: '#666',
    fontSize: 14,
    marginTop: 8,
  },
  inputContainer: {
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
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
    color: '#333',
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
  row: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  halfInput: {
    flex: 1,
  },
  saveButton: {
    backgroundColor: '#007bff',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 24,
  },
  saveButtonDisabled: {
    backgroundColor: '#ccc',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
});