export type RootStackParamList = {
    Login: undefined;
    Main: undefined;
};

export interface BotStatus {
    id: number;
    is_active: boolean;
    status_message: string;
    last_updated: string;
}

export interface BotConfig {
    id: number;
    mt5_login: string;
    mt5_password?: string; // Optional/Hidden in some views
    mt5_server: string;
    small_profit_usd: number;
    profit_check_interval: number;
    max_lot_size: number;
    max_open_positions: number;
}
