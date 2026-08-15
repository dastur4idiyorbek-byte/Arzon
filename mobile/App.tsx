import React from "react";
import { View, ActivityIndicator } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";

import { colors } from "./src/theme";
import { AuthProvider, useAuth } from "./src/auth/AuthContext";
import LoginScreen from "./src/screens/LoginScreen";
import CatalogScreen from "./src/screens/CatalogScreen";
import PlaceholderScreen from "./src/screens/PlaceholderScreen";

const Tab = createBottomTabNavigator();

function CartScreen() {
  return <PlaceholderScreen icon="🛒" title="Savat" sub="3-bosqichда: savat va checkout (ACOM balansdan to'lash)." />;
}
function OrdersScreen() {
  return <PlaceholderScreen icon="📦" title="Buyurtmalarim" sub="3-bosqichда: buyurtma holati + push-bildirishnoma." />;
}

function ProfileScreen() {
  const { user, roles, signOut } = useAuth();
  return (
    <PlaceholderScreen
      icon="👤"
      title={user?.ism || user?.email || "Profil"}
      sub={`Rollar: ${roles.join(", ")}\n\nRol-asosli ekranlar 4-bosqichда. Chiqish uchun bosing.`}
      onPress={signOut}
      buttonLabel="Chiqish"
    />
  );
}

// Rol-asosli navigatsiya (hozir mijoz tablari; admin/moliya/menejer 4-bosqichда).
function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarIcon: ({ color, size }) => {
          const map: Record<string, keyof typeof Ionicons.glyphMap> = {
            Katalog: "storefront-outline",
            Savat: "cart-outline",
            Buyurtmalar: "cube-outline",
            Profil: "person-outline",
          };
          return <Ionicons name={map[route.name] ?? "ellipse"} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="Katalog" component={CatalogScreen} />
      <Tab.Screen name="Savat" component={CartScreen} />
      <Tab.Screen name="Buyurtmalar" component={OrdersScreen} />
      <Tab.Screen name="Profil" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

function Root() {
  const { loading, user } = useAuth();
  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.bg }}>
        <ActivityIndicator size="large" color={colors.brand} />
      </View>
    );
  }
  return user ? <MainTabs /> : <LoginScreen />;
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <StatusBar style="dark" />
        <Root />
      </NavigationContainer>
    </AuthProvider>
  );
}
