"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getToken, clearToken } from "@/lib/api";

type AuthContextType = {
  token: string | null;
  setToken: (t: string | null) => void;
  isReady: boolean;
};

const AuthContext = createContext<AuthContextType>({
  token: null,
  setToken: () => {},
  isReady: false,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setTokenState(getToken());
    setIsReady(true);
  }, []);

  const setToken = (t: string | null) => {
    if (t === null) {
      clearToken();
      setTokenState(null);
    } else {
      if (typeof window !== "undefined") {
        window.localStorage.setItem("flowbase_token", t);
      }
      setTokenState(t);
    }
  };

  return (
    <AuthContext.Provider value={{ token, setToken, isReady }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
