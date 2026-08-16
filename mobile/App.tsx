import React, { useEffect, useRef } from "react";
import { View, ActivityIndicator } from "react-native";
import { StatusBar } from "expo-status-bar";
import * as Notifications from "expo-notifications";
import { NavigationContainer, createNavigationContainerRef } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";

import { colors } from "./src/theme";
import { AuthProvider, useAuth } from "./src/auth/AuthContext";
import { CartProvider, useCart } from "./src/cart/CartContext";
import { PromptProvider } from "./src/ui/Prompt";
import { useOtaUpdate } from "./src/useOtaUpdate";
import LoginScreen from "./src/screens/LoginScreen";
import CatalogScreen from "./src/screens/CatalogScreen";
import ProductScreen from "./src/screens/ProductScreen";
import CartScreen from "./src/screens/CartScreen";
import OrdersScreen from "./src/screens/OrdersScreen";
import BalanceScreen from "./src/screens/BalanceScreen";
import TopupScreen from "./src/screens/TopupScreen";
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
export const navigationRef = createNavigationContainerRef();

// Push bosilganда tegishli ekranga o'tish (Phase 5).
function handleNotificationNav(data: any) {
  if (!data || !navigationRef.isReady()) return;
  if (data.type === "order") navigationRef.navigate("Main" as never, { screen: "Buyurtmalar" } as never);
  else if (data.type === "balance") navigationRef.navigate("Main" as never, { screen: "Balans" } as never);
}

const stackScreenOptions = {
  headerTintColor: colors.brand,
  headerTitleStyle: { color: colors.text, fontWeight: "700" as const },
  headerStyle: { backgroundColor: colors.bg },
  headerShadowVisible: false,
  // Silliq, kutilgan o'tish (Android'da standart "fade"dan ko'ra tabiiyroq).
  animation: "slide_from_right" as const,
  animationDuration: 220,
  contentStyle: { backgroundColor: colors.bg },
};

function CatalogStack() {
  return (
    <Stack.Navigator screenOptions={stackScreenOptions}>
      <Stack.Screen name="Katalog" component={CatalogScreen} options={{ headerShown: false }} />
      <Stack.Screen name="Product" component={ProductScreen} options={{ headerShown: false }} />
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
        tabBarStyle: {
          backgroundColor: colors.bg,
          borderTopColor: colors.lineSoft,
          borderTopWidth: 1,
          height: 62,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "700" },
        tabBarIcon: ({ color, size, focused }) => {
          // Faol bo'lganda to'ldirilgan ikonka — joriy bo'lim aniq ko'rinsin.
          const map: Record<string, [keyof typeof Ionicons.glyphMap, keyof typeof Ionicons.glyphMap]> = {
            KatalogTab: ["storefront", "storefront-outline"],
            Savat: ["bag", "bag-outline"],
            Buyurtmalar: ["cube", "cube-outline"],
            Balans: ["person-circle", "person-circle-outline"],
          };
          const juft = map[route.name];
          const nomi = juft ? (focused ? juft[0] : juft[1]) : "ellipse";
          return <Ionicons name={nomi} size={size} color={color} />;
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
      <Root.Screen name="Topup" component={TopupScreen} options={{ title: "Hisobni to'ldirish" }} />
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
  // Ilova ochilganda yangilanishni tekshiradi va o'zi qo'llaydi (OTA).
  useOtaUpdate();

  useEffect(() => {
    // Foydalanuvchi push'ни bosганда tegishli ekranга o'tamiz.
    const sub = Notifications.addNotificationResponseReceivedListener((resp) => {
      handleNotificationNav(resp.notification.request.content.data);
    });
    // Ilova push orqali ochilган bo'lsa.
    Notifications.getLastNotificationResponseAsync().then((resp) => {
      if (resp) handleNotificationNav(resp.notification.request.content.data);
    });
    return () => sub.remove();
  }, []);

  return (
    <PromptProvider>
      <AuthProvider>
        <CartProvider>
          <NavigationContainer ref={navigationRef}>
            <StatusBar style="dark" />
            <RootNav />
          </NavigationContainer>
        </CartProvider>
      </AuthProvider>
    </PromptProvider>
  );
}
