/* SPDX-License-Identifier: GPL-2.0 */
/* Linux 6.1 compatibility helpers copied from the pinned Linux upstream
 * netdev_queues.h and drivers/net/can/dev/dev.c; original notices preserved
 * in the source archive. Only helper names are prefixed for isolation.
 */
#ifndef LBM5_COMPAT_H
#define LBM5_COMPAT_H
#include <linux/bitfield.h>
#include <linux/can/dev.h>
#include <linux/can/error.h>
#include <linux/netdevice.h>
#ifndef FIELD_PREP_CONST
#define FIELD_PREP_CONST(mask, value) (((typeof(mask))(value) << __bf_shf(mask)) & (mask))
#endif
#define lbm5_netif_txq_try_stop(txq, get_desc, start_thrs)			\
	({								\
		int _res;						\
									\
		netif_tx_stop_queue(txq);				\
		/* Producer index and stop bit must be visible		\
		 * to consumer before we recheck.			\
		 * Pairs with a barrier in lbm5___lbm5_netif_txq_completed_wake(). \
		 */							\
		smp_mb__after_atomic();					\
									\
		/* We need to check again in a case another		\
		 * CPU has just made room available.			\
		 */							\
		_res = 0;						\
		if (unlikely(get_desc >= start_thrs)) {			\
			netif_tx_start_queue(txq);			\
			_res = -1;					\
		}							\
		_res;							\
	})								\

/**
 * lbm5_netif_txq_maybe_stop() - locklessly stop a Tx queue, if needed
 * @txq:	struct netdev_queue to stop/start
 * @get_desc:	get current number of free descriptors (see requirements below!)
 * @stop_thrs:	minimal number of available descriptors for queue to be left
 *		enabled
 * @start_thrs:	minimal number of descriptors to re-enable the queue, can be
 *		equal to @stop_thrs or higher to avoid frequent waking
 *
 * All arguments may be evaluated multiple times, beware of side effects.
 * @get_desc must be a formula or a function call, it must always
 * return up-to-date information when evaluated!
 * Expected to be used from ndo_start_xmit, see the comment on top of the file.
 *
 * Returns:
 *	 0 if the queue was stopped
 *	 1 if the queue was left enabled
 *	-1 if the queue was re-enabled (raced with waking)
 */
#define lbm5_netif_txq_maybe_stop(txq, get_desc, stop_thrs, start_thrs)	\
	({								\
		int _res;						\
									\
		_res = 1;						\
		if (unlikely(get_desc < stop_thrs))			\
			_res = lbm5_netif_txq_try_stop(txq, get_desc, start_thrs); \
		_res;							\
	})								\

/* Variant of netdev_tx_completed_queue() which guarantees smp_mb() if
 * @bytes != 0, regardless of kernel config.
 */
static inline void
lbm5_netdev_txq_completed_mb(struct netdev_queue *dev_queue,
			unsigned int pkts, unsigned int bytes)
{
	if (IS_ENABLED(CONFIG_BQL))
		netdev_tx_completed_queue(dev_queue, pkts, bytes);
	else if (bytes)
		smp_mb();
}

/**
 * lbm5___lbm5_netif_txq_completed_wake() - locklessly wake a Tx queue, if needed
 * @txq:	struct netdev_queue to stop/start
 * @pkts:	number of packets completed
 * @bytes:	number of bytes completed
 * @get_desc:	get current number of free descriptors (see requirements below!)
 * @start_thrs:	minimal number of descriptors to re-enable the queue
 * @down_cond:	down condition, predicate indicating that the queue should
 *		not be woken up even if descriptors are available
 *
 * All arguments may be evaluated multiple times.
 * @get_desc must be a formula or a function call, it must always
 * return up-to-date information when evaluated!
 * Reports completed pkts/bytes to BQL.
 *
 * Returns:
 *	 0 if the queue was woken up
 *	 1 if the queue was already enabled (or disabled but @down_cond is true)
 *	-1 if the queue was left unchanged (@start_thrs not reached)
 */
#define lbm5___lbm5_netif_txq_completed_wake(txq, pkts, bytes,			\
				   get_desc, start_thrs, down_cond)	\
	({								\
		int _res;						\
									\
		/* Report to BQL and piggy back on its barrier.		\
		 * Barrier makes sure that anybody stopping the queue	\
		 * after this point sees the new consumer index.	\
		 * Pairs with barrier in lbm5_netif_txq_try_stop().		\
		 */							\
		lbm5_netdev_txq_completed_mb(txq, pkts, bytes);		\
									\
		_res = -1;						\
		if (pkts && likely(get_desc >= start_thrs)) {		\
			_res = 1;					\
			if (unlikely(netif_tx_queue_stopped(txq)) &&	\
			    !(down_cond)) {				\
				netif_tx_wake_queue(txq);		\
				_res = 0;				\
			}						\
		}							\
		_res;							\
	})

#define lbm5_netif_txq_completed_wake(txq, pkts, bytes, get_desc, start_thrs) \
	lbm5___lbm5_netif_txq_completed_wake(txq, pkts, bytes, get_desc, start_thrs, false)
#define lbm5_netif_subqueue_maybe_stop(dev, idx, get_desc, stop_thrs, start_thrs) \
	({								\
		struct netdev_queue *_txq;				\
									\
		_txq = netdev_get_tx_queue(dev, idx);			\
		lbm5_netif_txq_maybe_stop(_txq, get_desc, stop_thrs, start_thrs); \
	})

#define lbm5_netif_subqueue_completed_wake(dev, idx, pkts, bytes,		\
				      get_desc, start_thrs)		\
	({								\
		struct netdev_queue *_txq;				\
									\
		_txq = netdev_get_tx_queue(dev, idx);			\
		lbm5_netif_txq_completed_wake(_txq, pkts, bytes,		\
					 get_desc, start_thrs);		\
	})
static enum can_state lbm5_can_state_err_to_state(u16 err)
{
	if (err < CAN_ERROR_WARNING_THRESHOLD)
		return CAN_STATE_ERROR_ACTIVE;
	if (err < CAN_ERROR_PASSIVE_THRESHOLD)
		return CAN_STATE_ERROR_WARNING;
	if (err < CAN_BUS_OFF_THRESHOLD)
		return CAN_STATE_ERROR_PASSIVE;

	return CAN_STATE_BUS_OFF;
}

static inline void lbm5_can_state_get_by_berr_counter(const struct net_device *dev,
				   const struct can_berr_counter *bec,
				   enum can_state *tx_state,
				   enum can_state *rx_state)
{
	*tx_state = lbm5_can_state_err_to_state(bec->txerr);
	*rx_state = lbm5_can_state_err_to_state(bec->rxerr);
}

#endif
