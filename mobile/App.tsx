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
// Panel ekranlari (rol asosida — 4-bosqich)
import AdminHomeScreen from "./src/screens/panels/AdminHomeScreen";
import AdminProductsScreen from "./src/screens/panels/AdminProductsScreen";
import AdminProductEditScreen from "./src/screens/panels/AdminProductEditScreen";
import AdminOrdersScreen from "./src/screens/panels/AdminOrdersScreen";
import AdminStatsScreen from "./src/screens/panels/AdminStatsScreen";
import AdminWithdrawScreen from "./src/screens/panels/AdminWithdrawScreen";
import MoliyaHomeScreen from "./src/screens/panels/MoliyaHomeScreen";
import MenejerHomeScreen from "./src/screens/panels/MenejerHomeScreen";

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();
const Root = createNativeStackNavigator();

const stackScreenOptions = {
  headerTintColor: colors.brand,
  headerTitleStyle: { color: colors.text },
  headerStyle: { backgroundColor: colors.bg },
};

function CatalogStack() {
  return (
    <Stack.Navigator screenOptions={stackScreenOptions}>
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
      <Tab.Screen name="Balans" component={BalanceScreen} options={{ title: "Profil" }} />
    </Tab.Navigator>
  );
}

function RootNav() {
  const { loading, user } = useAuth();
  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.bg }}>
        <ActivityIndicator size="large" color={colors.brand} />
      </View>
    );
  }
  if (!user) return <LoginScreen />;
  return (
    <Root.Navigator screenOptions={stackScreenOptions}>
      <Root.Screen name="Main" component={MainTabs} options={{ headerShown: false }} />
      {/* Admin paneli */}
      <Root.Screen name="AdminHome" component={AdminHomeScreen} options={{ title: "🛠 Admin paneli" }} />
      <Root.Screen name="AdminProducts" component={AdminProductsScreen} options={{ title: "Mahsulotlar" }} />
      <Root.Screen name="AdminProductEdit" component={AdminProductEditScreen} options={{ title: "Mahsulot" }} />
      <Root.Screen name="AdminOrders" component={AdminOrdersScreen} options={{ title: "Buyurtmalar" }} />
      <Root.Screen name="AdminStats" component={AdminStatsScreen} options={{ title: "Statistika" }} />
      <Root.Screen name="AdminWithdraw" component={AdminWithdrawScreen} options={{ title: "Pul yechish" }} />
      {/* Moliya paneli */}
      <Root.Screen name="MoliyaHome" component={MoliyaHomeScreen} options={{ title: "💰 Moliya paneli" }} />
      {/* Menejer paneli */}
      <Root.Screen name="MenejerHome" component={MenejerHomeScreen} options={{ title: "👔 Menejer paneli" }} />
    </Root.Navigator>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <NavigationContainer>
          <StatusBar style="dark" />
          <RootNav />
        </NavigationContainer>
      </CartProvider>
    </AuthProvider>
  );
}
