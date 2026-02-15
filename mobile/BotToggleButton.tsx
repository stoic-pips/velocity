/**
 * Dunam Velocity – Bot Toggle Button
 *
 * A self-contained React Native component that toggles the MT5 scalping bot
 * on/off by sending a POST request to the Python backend.
 */

import React, { useState, useCallback } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ActivityIndicator,
    Alert,
    StyleSheet,
} from "react-native";
import { startBot, stopBot, getStatus } from "./api";

const BotToggleButton: React.FC = () => {
    const [isRunning, setIsRunning] = useState(false);
    const [loading, setLoading] = useState(false);

    // ── Toggle handler ─────────────────────────────────────────────────────
    const handleToggle = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = isRunning ? await stopBot() : await startBot();
            setIsRunning(data.running);
            Alert.alert(
                data.running ? "Bot Activated ✅" : "Bot Stopped 🛑",
                data.status
            );
        } catch (err: unknown) {
            const message =
                err instanceof Error ? err.message : "Unexpected error";
            Alert.alert("Connection Error", message);
        } finally {
            setLoading(false);
        }
    }, []);

    // ── Refresh status ─────────────────────────────────────────────────────
    const handleRefresh = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await getStatus();
            setIsRunning(data.bot.running);
        } catch {
            // silent – we'll just keep the last known state
        } finally {
            setLoading(false);
        }
    }, []);

    // ── Render ─────────────────────────────────────────────────────────────
    return (
        <View style={styles.container}>
            {/* Title */}
            <Text style={styles.title}>Dunam Velocity</Text>
            <Text style={styles.subtitle}>MT5 Scalping Bot Control</Text>

            {/* Status badge */}
            <View style={[styles.badge, isRunning ? styles.badgeOn : styles.badgeOff]}>
                <View style={[styles.dot, isRunning ? styles.dotOn : styles.dotOff]} />
                <Text style={styles.badgeText}>
                    {isRunning ? "RUNNING" : "STOPPED"}
                </Text>
            </View>

            {/* Toggle button */}
            <TouchableOpacity
                style={[
                    styles.button,
                    isRunning ? styles.buttonOff : styles.buttonOn,
                    loading && styles.buttonDisabled,
                ]}
                onPress={handleToggle}
                disabled={loading}
                activeOpacity={0.8}
            >
                {loading ? (
                    <ActivityIndicator color="#fff" size="small" />
                ) : (
                    <Text style={styles.buttonText}>
                        {isRunning ? "⏹  STOP BOT" : "▶  START BOT"}
                    </Text>
                )}
            </TouchableOpacity>

            {/* Refresh link */}
            <TouchableOpacity onPress={handleRefresh} disabled={loading}>
                <Text style={styles.refresh}>↻ Refresh Status</Text>
            </TouchableOpacity>
        </View>
    );
};

// ── Styles ─────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#0f0f14",
        padding: 32,
    },
    title: {
        fontSize: 28,
        fontWeight: "800",
        color: "#ffffff",
        letterSpacing: 1.2,
    },
    subtitle: {
        fontSize: 14,
        color: "#8888aa",
        marginBottom: 40,
        letterSpacing: 0.5,
    },

    // Status badge
    badge: {
        flexDirection: "row",
        alignItems: "center",
        paddingVertical: 8,
        paddingHorizontal: 20,
        borderRadius: 999,
        marginBottom: 32,
    },
    badgeOn: { backgroundColor: "rgba(34,197,94,0.15)" },
    badgeOff: { backgroundColor: "rgba(239,68,68,0.15)" },
    badgeText: {
        fontSize: 13,
        fontWeight: "700",
        color: "#ffffff",
        letterSpacing: 2,
    },
    dot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        marginRight: 10,
    },
    dotOn: { backgroundColor: "#22c55e" },
    dotOff: { backgroundColor: "#ef4444" },

    // Toggle button
    button: {
        width: 220,
        paddingVertical: 16,
        borderRadius: 14,
        alignItems: "center",
        marginBottom: 20,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 6,
        elevation: 6,
    },
    buttonOn: { backgroundColor: "#22c55e" },
    buttonOff: { backgroundColor: "#ef4444" },
    buttonDisabled: { opacity: 0.6 },
    buttonText: {
        fontSize: 16,
        fontWeight: "700",
        color: "#ffffff",
        letterSpacing: 1,
    },

    // Refresh
    refresh: {
        fontSize: 13,
        color: "#6366f1",
        marginTop: 8,
    },
});

export default BotToggleButton;
