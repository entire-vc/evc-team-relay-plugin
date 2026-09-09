import { CredentialCache } from "../src/CredentialCache";
import { MockClock } from "./mocks/MockClock";
import { describe, expect, test } from "@jest/globals";

// #75491f2f: control-plane issues relay tokens with a 5-minute TTL
// (relay_token_ttl_minutes, a deliberate H6 security bound -- not something
// this test touches). CredentialCache's renewalMargin must stay meaningfully
// below that TTL, or needsRefresh() collapses to "refresh the instant the
// token is issued" and every open share gets re-issued + reconnected on
// literally every 60s sweep tick forever, instead of once per TTL window.
interface TestToken {
	token: string;
}

const MINUTE_MS = 60 * 1000;
const TTL_MS = 5 * MINUTE_MS;

function buildStore(clock: MockClock, refreshCounter: { count: number }) {
	const mockRefresh = (_documentId: string, onSuccess: (token: TestToken) => void) => {
		refreshCounter.count++;
		onSuccess({ token: (clock.now() + TTL_MS).toString() });
	};
	return new CredentialCache<TestToken>(
		{
			logMessage: () => undefined,
			refreshToken: mockRefresh,
			getClock: () => clock,
			getTokenExpiry: (t) => parseInt(t.token, 10),
		},
		1,
	);
}

describe("CredentialCache renewal margin vs token TTL (#75491f2f)", () => {
	test("an open share is not re-issued on every 60s sweep tick over a 5-minute TTL", async () => {
		const clock = new MockClock();
		const counter = { count: 0 };
		const store = buildStore(clock, counter);

		await store.acquireToken("doc1", "doc1", () => undefined);
		expect(counter.count).toBe(1); // initial issuance, not a sweep refresh

		store.startSweeping();
		const startCount = counter.count;
		for (let i = 0; i < 20; i++) {
			clock.setTime(clock.now() + MINUTE_MS); // 20 sweep ticks = 20 simulated minutes
		}
		store.stopSweeping();
		const sweepRefreshes = counter.count - startCount;

		// With a healthy margin (well below the 5-minute TTL) an open share
		// should need re-issuing roughly once per (TTL - margin) window --
		// at most ~8 times over 20 minutes. The storm bug (margin == TTL)
		// re-issues on effectively every single tick (~19-20 times).
		expect(sweepRefreshes).toBeLessThanOrEqual(8);
	});
});
