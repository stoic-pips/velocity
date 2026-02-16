import React, { useEffect, useState } from 'react';
import { View, Text, TextInput, ScrollView, StyleSheet, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useForm, Controller } from 'react-hook-form';
import { supabase } from '../lib/supabase';
import { BotConfig } from '../types';
import { LucideSave, LucideServer, LucideShieldAlert, LucideDollarSign } from 'lucide-react-native';

const ConfigScreen = () => {
    const { control, handleSubmit, setValue, formState: { errors } } = useForm<BotConfig>();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchConfig();
    }, []);

    const fetchConfig = async () => {
        const { data, error } = await supabase
            .from('config')
            .select('*')
            .single();

        if (error) {
            console.error('Error fetching config:', error);
            Alert.alert('Error', 'Failed to load configuration.');
        } else if (data) {
            // Populate form
            Object.keys(data).forEach(key => {
                setValue(key as keyof BotConfig, data[key]);
            });
        }
        setLoading(false);
    };

    const onSubmit = async (data: BotConfig) => {
        setSaving(true);
        const { error } = await supabase
            .from('config')
            .update(data)
            .eq('id', data.id);

        if (error) {
            Alert.alert('Error', error.message);
        } else {
            Alert.alert('Success', 'Configuration updated successfully.');
        }
        setSaving(false);
    };

    if (loading) {
        return (
            <View style={[styles.container, styles.center]}>
                <ActivityIndicator size="large" color="#ffffff" />
            </View>
        );
    }

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <View style={styles.header}>
                <Text style={styles.title}>Configuration</Text>
                <Text style={styles.subtitle}>Risk Management & Credentials</Text>
            </View>

            {/* MT5 Section */}
            <View style={styles.section}>
                <View style={styles.sectionHeader}>
                    <LucideServer size={20} color="#6366f1" />
                    <Text style={styles.sectionTitle}>MT5 Credentials</Text>
                </View>

                <Controller
                    control={control}
                    name="mt5_login"
                    rules={{ required: 'Login ID is required' }}
                    render={({ field: { onChange, value } }) => (
                        <View style={styles.inputGroup}>
                            <Text style={styles.label}>Login ID</Text>
                            <TextInput
                                style={styles.input}
                                value={String(value || '')}
                                onChangeText={onChange}
                                keyboardType="numeric"
                                placeholder="12345678"
                                placeholderTextColor="#52525b"
                            />
                            {errors.mt5_login && <Text style={styles.errorText}>{errors.mt5_login.message}</Text>}
                        </View>
                    )}
                />

                <Controller
                    control={control}
                    name="mt5_password"
                    rules={{ required: 'Password is required' }}
                    render={({ field: { onChange, value } }) => (
                        <View style={styles.inputGroup}>
                            <Text style={styles.label}>Password</Text>
                            <TextInput
                                style={styles.input}
                                value={value}
                                onChangeText={onChange}
                                secureTextEntry
                                placeholder="••••••••"
                                placeholderTextColor="#52525b"
                            />
                        </View>
                    )}
                />

                <Controller
                    control={control}
                    name="mt5_server"
                    rules={{ required: 'Server is required' }}
                    render={({ field: { onChange, value } }) => (
                        <View style={styles.inputGroup}>
                            <Text style={styles.label}>Server</Text>
                            <TextInput
                                style={styles.input}
                                value={value}
                                onChangeText={onChange}
                                placeholder="MetaQuotes-Demo"
                                placeholderTextColor="#52525b"
                            />
                        </View>
                    )}
                />
            </View>

            {/* Scalper Logic Section */}
            <View style={styles.section}>
                <View style={styles.sectionHeader}>
                    <LucideDollarSign size={20} color="#22c55e" />
                    <Text style={styles.sectionTitle}>Scalper Logic</Text>
                </View>

                <Controller
                    control={control}
                    name="small_profit_usd"
                    rules={{ required: true, min: 0 }}
                    render={({ field: { onChange, value } }) => (
                        <View style={styles.inputGroup}>
                            <Text style={styles.label}>Small Profit Target (USD)</Text>
                            <TextInput
                                style={styles.input}
                                value={String(value || '')}
                                onChangeText={(text) => onChange(Number(text))}
                                keyboardType="numeric"
                            />
                        </View>
                    )}
                />

                <Controller
                    control={control}
                    name="profit_check_interval"
                    rules={{ required: true, min: 1 }}
                    render={({ field: { onChange, value } }) => (
                        <View style={styles.inputGroup}>
                            <Text style={styles.label}>Check Interval (Seconds)</Text>
                            <TextInput
                                style={styles.input}
                                value={String(value || '')}
                                onChangeText={(text) => onChange(Number(text))}
                                keyboardType="numeric"
                            />
                        </View>
                    )}
                />
            </View>

            {/* Risk Limits Section */}
            <View style={styles.section}>
                <View style={styles.sectionHeader}>
                    <LucideShieldAlert size={20} color="#ef4444" />
                    <Text style={styles.sectionTitle}>Risk Limits</Text>
                </View>

                <View style={styles.row}>
                    <Controller
                        control={control}
                        name="max_lot_size"
                        rules={{ required: true, min: 0.01 }}
                        render={({ field: { onChange, value } }) => (
                            <View style={[styles.inputGroup, { flex: 1, marginRight: 8 }]}>
                                <Text style={styles.label}>Max Lot Size</Text>
                                <TextInput
                                    style={styles.input}
                                    value={String(value || '')}
                                    onChangeText={(text) => onChange(Number(text))}
                                    keyboardType="numeric"
                                />
                            </View>
                        )}
                    />

                    <Controller
                        control={control}
                        name="max_open_positions"
                        rules={{ required: true, min: 1 }}
                        render={({ field: { onChange, value } }) => (
                            <View style={[styles.inputGroup, { flex: 1, marginLeft: 8 }]}>
                                <Text style={styles.label}>Max Positions</Text>
                                <TextInput
                                    style={styles.input}
                                    value={String(value || '')}
                                    onChangeText={(text) => onChange(Number(text))}
                                    keyboardType="numeric"
                                />
                            </View>
                        )}
                    />
                </View>
            </View>

            <TouchableOpacity
                style={styles.saveButton}
                onPress={handleSubmit(onSubmit)}
                disabled={saving}
            >
                {saving ? (
                    <ActivityIndicator color="#000" />
                ) : (
                    <>
                        <LucideSave size={20} color="#000" style={{ marginRight: 8 }} />
                        <Text style={styles.saveButtonText}>Save Configuration</Text>
                    </>
                )}
            </TouchableOpacity>
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
        marginBottom: 32,
        marginTop: 16,
    },
    title: {
        fontSize: 28,
        fontWeight: '800',
        color: '#ffffff',
    },
    subtitle: {
        fontSize: 14,
        color: '#71717a',
        marginTop: 4,
    },
    section: {
        marginBottom: 32,
    },
    sectionHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
        gap: 8,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: '#ffffff',
    },
    inputGroup: {
        marginBottom: 16,
    },
    label: {
        color: '#a1a1aa',
        fontSize: 14,
        marginBottom: 8,
    },
    input: {
        backgroundColor: '#18181b',
        borderWidth: 1,
        borderColor: '#27272a',
        borderRadius: 8,
        padding: 12,
        color: '#ffffff',
        fontSize: 16,
    },
    row: {
        flexDirection: 'row',
    },
    errorText: {
        color: '#ef4444',
        fontSize: 12,
        marginTop: 4,
    },
    saveButton: {
        backgroundColor: '#ffffff',
        borderRadius: 12,
        height: 56,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: 16,
    },
    saveButtonText: {
        color: '#000000',
        fontSize: 16,
        fontWeight: '700',
    },
});

export default ConfigScreen;
