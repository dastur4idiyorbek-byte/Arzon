import React from "react";
import { View, ActivityIndicator } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";

import { colors } from "./src/theme";
import { AuthProvider, useAuth } from "./src/auth/AuthContext";
import { CartProvider, useCart } from "./src/cart/CartContext";
import LoginScreen from "./src/screens/LoginScreen";
import CatalogScreen from "./src/screens/CatalogScreen";
import ProductScreen from "./src/screens/ProductScreen";
import CartScreen from "./src/screens/CartScreen";
import OrdersScreen from "./src/screens/OrdersScreen";
import BalanceScreen from "./src/screens/BalanceScreen";

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

function CatalogStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerTintColor: colors.brand,
        headerTitleStyle: { color: colors.text },
      }}
    >
      <Stack.Screen name="Katalog" component={CatalogScreen} options={{ headerShown: false }} />
      <Stack.Screen name="Product" component={ProductScreen} options={{ title: "Mahsulot" }} />
    </Stack.Navigator>
  );
}

function MainTabs() {
  const { count } = useCart();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarIcon: ({ color, size }) => {
          const map: Record<string, keyof typeof Ionicons.glyphMap> = {
            KatalogTab: "storefront-outline",
            Savat: "cart-outline",
            Buyurtmalar: "cube-outline",
            Balans: "wallet-outline",
          };
          return <Ionicons name={map[route.name] ?? "ellipse"} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="KatalogTab" component={CatalogStack} options={{ title: "Katalog" }} />
      <Tab.Screen name="Savat" component={CartScreen} options={{ tabBarBadge: count || undefined }} />
      <Tab.Screen name="Buyurtmalar" component={OrdersScreen} />
      <Tab.Screen name="Balans" component={BalanceScreen} />
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
      <CartProvider>
        <NavigationContainer>
          <StatusBar style="dark" />
          <Root />
        </NavigationContainer>
      </CartProvider>
    </AuthProvider>
  );
}
