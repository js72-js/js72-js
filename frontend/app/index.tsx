import React, { useEffect, useState } from 'react';
import { View, StyleSheet, Image } from 'react-native';
import { router } from 'expo-router';

export default function SplashScreen() {
  const [timeLeft, setTimeLeft] = useState(20);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          router.replace('/auth/login');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <View style={styles.container}>
      <Image
        source={require("../assets/images/app-image.png")}
        style={styles.image}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0c0c0c",
    alignItems: "center",
    justifyContent: "center",
  },
  image: {
    width: "80%",
    height: "60%",
    resizeMode: "contain",
  },
});