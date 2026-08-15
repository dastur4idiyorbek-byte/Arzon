import React from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";

import { colors } from "./src/theme";
import CatalogScreen from "./src/screens/CatalogScreen";
import PlaceholderScreen from "./src/screens/PlaceholderScreen";

const Tab = createBottomTabNavigator();

// 1-bosqich: mijoz navigatsiyasi (asos). Rol-asosli navigatsiya 2-bosqichда.
function CartScreen() {
  return <PlaceholderScreen icon="🛒" title="Savat" sub="3-bosqichда: savat va checkout (ACOM balansdan to'lash)." />;
}
function OrdersScreen() {
  return <PlaceholderScreen icon="📦" title="Buyurtmalarim" sub="3-bosqichда: buyurtma holati + push-bildirishnoma." />;
}
function ProfileScreen() {
  return <PlaceholderScreen icon="👤" title="Profil" sub="2-bosqichда: kirish (Google/Apple/Email), rol almashtirish." />;
}

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="dark" />
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
    </NavigationContainer>
  );
}
