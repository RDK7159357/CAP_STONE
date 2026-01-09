/**
 * Date and Time Utilities
 */

import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import customParseFormat from 'dayjs/plugin/customParseFormat';

dayjs.extend(relativeTime);
dayjs.extend(customParseFormat);

export const DateUtils = {
  /**
   * Format date to readable string
   */
  format: (date: string | Date, format: string = 'YYYY-MM-DD HH:mm') => {
    return dayjs(date).format(format);
  },

  /**
   * Get relative time (e.g., "2 hours ago")
   */
  fromNow: (date: string | Date) => {
    return dayjs(date).fromNow();
  },

  /**
   * Parse date from string
   */
  parse: (dateString: string, format: string) => {
    return dayjs(dateString, format);
  },

  /**
   * Get today's date
   */
  today: () => {
    return dayjs().format('YYYY-MM-DD');
  },

  /**
   * Check if date is today
   */
  isToday: (date: string | Date) => {
    return dayjs(date).isSame(dayjs(), 'day');
  },

  /**
   * Get start and end of day
   */
  getDayRange: (date: string | Date) => {
    const d = dayjs(date);
    return {
      start: d.startOf('day').toISOString(),
      end: d.endOf('day').toISOString(),
    };
  },
};

export default DateUtils;
