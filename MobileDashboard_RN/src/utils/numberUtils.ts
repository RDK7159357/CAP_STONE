/**
 * Number and Format Utilities
 */

export const NumberUtils = {
  /**
   * Format number with thousand separators
   */
  formatNumber: (num: number): string => {
    return num.toLocaleString();
  },

  /**
   * Round to specific decimal places
   */
  round: (num: number, decimals: number = 2): number => {
    return Math.round(num * Math.pow(10, decimals)) / Math.pow(10, decimals);
  },

  /**
   * Format bytes to human readable
   */
  formatBytes: (bytes: number, decimals: number = 2): string => {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round((bytes / Math.pow(k, i)) * Math.pow(10, dm)) / Math.pow(10, dm) + ' ' + sizes[i];
  },

  /**
   * Percentage calculation
   */
  percentageOf: (value: number, total: number): number => {
    return (value / total) * 100;
  },

  /**
   * Format percentage
   */
  formatPercentage: (value: number, decimals: number = 1): string => {
    return `${value.toFixed(decimals)}%`;
  },
};

export default NumberUtils;
