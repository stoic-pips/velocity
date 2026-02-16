'use client';

import { useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { TrendingUp, Lock, Mail, UserPlus, AlertCircle, CheckCircle } from 'lucide-react';
import clsx from 'clsx';

export default function Signup() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSignup = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            setLoading(false);
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            setLoading(false);
            return;
        }

        const { error } = await supabase.auth.signUp({
            email,
            password,
        });

        if (error) {
            setError(error.message);
            setLoading(false);
        } else {
            setSuccess(true);
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen bg-stoic-black flex flex-col items-center justify-center p-4">
                <div className="w-full max-w-md space-y-8">
                    <div className="flex flex-col items-center gap-2 mb-10">
                        <div className="p-4 rounded-2xl bg-stoic-charcoal border border-stoic-action/30 shadow-2xl shadow-stoic-action/10">
                            <CheckCircle className="w-10 h-10 text-stoic-action" />
                        </div>
                        <h1 className="text-3xl font-bold tracking-tight text-white mt-4">Account Created</h1>
                        <p className="text-gray-400 text-sm text-center max-w-xs">
                            Check your email for a confirmation link to activate your account.
                        </p>
                    </div>

                    <button
                        onClick={() => router.push('/login')}
                        className="w-full py-4 rounded-xl bg-stoic-action text-black font-bold uppercase tracking-widest hover:bg-stoic-action/90 transition-all shadow-[0_0_20px_rgba(0,255,65,0.2)]"
                    >
                        Go to Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-stoic-black flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-md space-y-8">
                {/* Logo Section */}
                <div className="flex flex-col items-center gap-2 mb-10">
                    <div className="p-4 rounded-2xl bg-stoic-charcoal border border-white/5 shadow-2xl shadow-stoic-action/5">
                        <TrendingUp className="w-10 h-10 text-stoic-action" />
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight text-white mt-4">VELOCITY</h1>
                    <p className="text-gray-500 text-sm tracking-widest uppercase font-medium">Create Account</p>
                </div>

                {/* Signup Form */}
                <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-8 shadow-xl backdrop-blur-sm">
                    <form onSubmit={handleSignup} className="space-y-6">

                        {error && (
                            <div className="bg-stoic-danger/10 border border-stoic-danger/20 text-stoic-danger p-4 rounded-xl flex items-center gap-3 text-sm">
                                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        <div className="space-y-2">
                            <label className="text-xs text-gray-400 uppercase font-bold tracking-wider ml-1">Email Identity</label>
                            <div className="relative group">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-stoic-action transition-colors" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="w-full bg-stoic-black/50 border border-white/10 rounded-xl py-4 pl-12 pr-4 text-white focus:border-stoic-action focus:ring-1 focus:ring-stoic-action outline-none transition-all placeholder:text-gray-700"
                                    placeholder="agent@example.com"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs text-gray-400 uppercase font-bold tracking-wider ml-1">Passcode</label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-stoic-action transition-colors" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    minLength={6}
                                    className="w-full bg-stoic-black/50 border border-white/10 rounded-xl py-4 pl-12 pr-4 text-white focus:border-stoic-action focus:ring-1 focus:ring-stoic-action outline-none transition-all placeholder:text-gray-700"
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs text-gray-400 uppercase font-bold tracking-wider ml-1">Confirm Passcode</label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-stoic-action transition-colors" />
                                <input
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                    minLength={6}
                                    className="w-full bg-stoic-black/50 border border-white/10 rounded-xl py-4 pl-12 pr-4 text-white focus:border-stoic-action focus:ring-1 focus:ring-stoic-action outline-none transition-all placeholder:text-gray-700"
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className={clsx(
                                "w-full py-4 rounded-xl font-bold uppercase tracking-widest flex items-center justify-center gap-3 transition-all duration-300",
                                loading
                                    ? "bg-stoic-gray text-gray-500 cursor-not-allowed"
                                    : "bg-stoic-action text-black hover:bg-stoic-action/90 shadow-[0_0_20px_rgba(0,255,65,0.2)] hover:shadow-[0_0_30px_rgba(0,255,65,0.4)]"
                            )}
                        >
                            {loading ? 'Creating Account...' : (
                                <>
                                    <span>Create Account</span>
                                    <UserPlus className="w-5 h-5" />
                                </>
                            )}
                        </button>
                    </form>
                </div>

                <p className="text-center text-gray-500 text-sm">
                    Already have access?{' '}
                    <Link href="/login" className="text-stoic-action hover:text-stoic-action/80 font-semibold transition-colors">
                        Sign In
                    </Link>
                </p>
            </div>
        </div>
    );
}
