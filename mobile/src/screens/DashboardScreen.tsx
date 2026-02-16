import React, { useState, useEffect } from 'react';
import { View, Text, Switch, StyleSheet, ActivityIndicator, Alert, ScrollView } from 'react-native';
import { supabase } from '../lib/supabase';
import { BotStatus } from '../types';
import { LucideActivity, LucideTrendingUp, LucidePower } from 'lucide-react-native';

const DashboardScreen = () => {
    const [status, setStatus] = useState<BotStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [toggling, setToggling] = useState(false);

    useEffect(() => {
        // Fetch initial status
        fetchStatus();

        // Subscribe to real-time changes
        const subscription = supabase
            .channel('public:bot_status')
            .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'bot_status' }, (payload) => {
                setStatus(payload.new as BotStatus);
            })
            .subscribe();

        return () => {
            supabase.removeChannel(subscription);
        };
    }, []);

    const fetchStatus = async () => {
        const { data, error } = await supabase
            .from('bot_status')
            .select('*')
            .single();

        if (error) console.error('Error fetching status:', error);
        else setStatus(data);
        setLoading(false);
    };

    const toggleBot = async (newValue: boolean) => {
        setToggling(true);
        // Optimistic update
        const previousStatus = status?.is_active;
        setStatus(prev => prev ? { ...prev, is_active: newValue } : null);

        const { error } = await supabase
            .from('bot_status')
            .update({ is_active: newValue })
            .eq('id', status?.id); // Assuming single row or specific ID

        if (error) {
            Alert.alert('Error', 'Failed to update bot status. reverting...');
            setStatus(prev => prev ? { ...prev, is_active: previousStatus || false } : null);
        }
        setToggling(false);
    };

    if (loading) {
        return (
            <View style={[styles.container, styles.center]}>
                <ActivityIndicator size="large" color="#ffffff" />
            </View>
        );
    }

    const isActive = status?.is_active ?? false;

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <View style={styles.header}>
                <Text style={styles.title}>Dashboard</Text>
                <View style={[styles.statusBadge, isActive ? styles.statusActive : styles.statusInactive]}>
                    <View style={[styles.statusDot, isActive ? styles.dotActive : styles.dotInactive]} />
                    <Text style={styles.statusText}>{isActive ? 'ONLINE' : 'OFFLINE'}</Text>
                </View>
            </View>

            {/* Main Toggle Card */}
            <View style={styles.card}>
                <View style={styles.cardHeader}>
                    <LucidePower size={24} color={isActive ? '#22c55e' : '#ef4444'} />
                    <Text style={styles.cardTitle}>Master Switch</Text>
                </View>
                <View style={styles.toggleContainer}>
                    <Text style={styles.toggleLabel}>{isActive ? 'System Active' : 'System Halted'}</Text>
                    <Switch
                        trackColor={{ false: '#3f3f46', true: 'rgba(34, 197, 94, 0.3)' }}
                        thumbColor={isActive ? '#22c55e' : '#f4f3f4'}
                        onValueChange={toggleBot}
                        value={isActive}
                        disabled={toggling}
                    />
                </View>
            </View>

            {/* Summary Metrics */}
            <View style={styles.grid}>
                <View style={styles.metricCard}>
                    <View style={styles.metricHeader}>
                        <LucideTrendingUp size={20} color="#22c55e" />
                        <Text style={styles.metricLabel}>Today's Profit</Text>
                    </View>
                    <Text style={styles.metricValue}>$ 124.50</Text>
                    <Text style={[styles.metricDelta, styles.positive]}>+2.4%</Text>
                </View>

                <View style={styles.metricCard}>
                    <View style={styles.metricHeader}>
                        <LucideActivity size={20} color="#3b82f6" />
                        <Text style={styles.metricLabel}>Open Positions</Text>
                    </View>
                    <Text style={styles.metricValue}>3</Text>
                    <Text style={styles.metricSub}>EURUSD, GBPUSD</Text>
                </View>
            </View>

            {/* Logs Preview (Optional/Placeholder) */}
            <View style={styles.card}>
                <Text style={styles.cardTitle}>Recent Activity</Text>
                <View style={styles.logItem}>
                    <Text style={styles.logTime}>10:42 AM</Text>
                    <Text style={styles.logMessage}>Closed Buy EURUSD (+ $5.20)</Text>
                </View>
                <View style={styles.logItem}>
                    <Text style={styles.logTime}>10:38 AM</Text>
                    <Text style={styles.logMessage}>Opened Buy EURUSD (1.0 Lot)</Text>
                </View>
            </View>
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0f0f14',
    },
    content: {
        padding: 24,
        paddingBottom: 48,
    },
    center: {
        justifyContent: 'center',
        alignItems: 'center',
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 32,
        marginTop: 16,
    },
    title: {
        fontSize: 28,
        fontWeight: '800',
        color: '#ffffff',
    },
    statusBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
        backgroundColor: 'rgba(39, 39, 42, 0.5)',
    },
    statusActive: {
        borderColor: '#22c55e',
        borderWidth: 1,
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
    },
    statusInactive: {
        borderColor: '#ef4444',
        borderWidth: 1,
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
    },
    statusDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        marginRight: 8,
    },
    dotActive: { backgroundColor: '#22c55e' },
    dotInactive: { backgroundColor: '#ef4444' },
    statusText: {
        color: '#ffffff',
        fontSize: 12,
        fontWeight: '700',
    },
    card: {
        backgroundColor: '#18181b',
        borderRadius: 16,
        padding: 20,
        marginBottom: 24,
        borderWidth: 1,
        borderColor: '#27272a',
    },
    cardHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
        gap: 12,
    },
    cardTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: '#ffffff',
    },
    toggleContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    toggleLabel: {
        color: '#a1a1aa',
        fontSize: 16,
    },
    grid: {
        flexDirection: 'row',
        gap: 16,
        marginBottom: 24,
    },
    metricCard: {
        flex: 1,
        backgroundColor: '#18181b',
        borderRadius: 16,
        padding: 16,
        borderWidth: 1,
        borderColor: '#27272a',
    },
    metricHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 12,
    },
    metricLabel: {
        color: '#a1a1aa',
        fontSize: 12,
        fontWeight: '600',
    },
    metricValue: {
        color: '#ffffff',
        fontSize: 24,
        fontWeight: '800',
        marginBottom: 4,
    },
    metricDelta: {
        fontSize: 12,
        fontWeight: '600',
    },
    metricSub: {
        fontSize: 12,
        color: '#71717a',
    },
    positive: {
        color: '#22c55e',
    },
    logItem: {
        borderBottomWidth: 1,
        borderBottomColor: '#27272a',
        paddingVertical: 12,
    },
    logTime: {
        color: '#71717a',
        fontSize: 12,
        marginBottom: 2,
    },
    logMessage: {
        color: '#e4e4e7',
        fontSize: 14,
    },
});

export default DashboardScreen;
