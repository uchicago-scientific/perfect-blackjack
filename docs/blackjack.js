// Blackjack by the lab's rules, for the web page: the game, the strategy
// charts, and the Monte Carlo that scores them.
//
// The rules are blackjack.py's: an infinite deck (every card drawn with
// replacement), hit or stand only, the dealer hits 16 or less and stands on
// 17 or more, soft 17 included, blackjack pays 3 to 2, and a dealer
// blackjack beats every other hand. There is no early check for dealer
// blackjack: it shows when the hole card turns over.
//
// A chart is 270 numbers, 1 for hit and 0 for stand, row by row: 27 rows
// (hard 4 to 21, then soft 13 to 21) of 10 columns (dealer 2 to 10, then
// ace). Cell 0 is hard 4 against a 2, cell 10 is hard 5 against a 2.

(function (root) {
  "use strict";

  const RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"];
  const SUITS = ["♠", "♥", "♦", "♣"];
  const VALUES = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11];   // 11 is an ace
  const UP_NAMES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "A"];
  const ROWS = [];
  for (let t = 4; t <= 21; t++) ROWS.push({ soft: false, total: t });
  for (let t = 13; t <= 21; t++) ROWS.push({ soft: true, total: t });
  const HAND_NAMES = ROWS.map((r) => (r.soft ? "S" : "H") + r.total);

  // ------------------------------------------------------------ charts

  // basic-strategy.csv and table-round-1.csv, one string per row.
  const BASIC = [
    "HHHHHHHHHH", "HHHHHHHHHH", "HHHHHHHHHH", "HHHHHHHHHH", "HHHHHHHHHH",
    "HHHHHHHHHH", "HHHHHHHHHH", "HHHHHHHHHH", "HHSSSHHHHH", "SSSSSHHHHH",
    "SSSSSHHHHH", "SSSSSHHHHH", "SSSSSHHHHH", "SSSSSSSSSS", "SSSSSSSSSS",
    "SSSSSSSSSS", "SSSSSSSSSS", "SSSSSSSSSS",
    "HHHHHHHHHH", "HHHHHHHHHH", "HHHHHHHHHH", "HHHHHHHHHH", "HHHHHHHHHH",
    "SSSSSSSHHH", "SSSSSSSSSS", "SSSSSSSSSS", "SSSSSSSSSS",
  ];
  const START = ROWS.map((r) => (r.total < 17 ? "H" : "S").repeat(10));

  function chartFromRows(rows) {
    const chart = new Uint8Array(270);
    rows.forEach((row, r) => {
      for (let c = 0; c < 10; c++) chart[r * 10 + c] = row[c] === "H" ? 1 : 0;
    });
    return chart;
  }

  const CHARTS = {
    basic: { name: "basic-strategy.csv", chart: chartFromRows(BASIC) },
    start: { name: "table-round-1.csv", chart: chartFromRows(START) },
  };

  // A table CSV (hand,2,...,10,A, then one row per hand of H or S) as a chart.
  // Throws an Error that says what is wrong.
  function parseChart(text) {
    const lines = text.replace(/\r/g, "").split("\n").map((l) => l.trim()).filter((l) => l);
    if (!lines.length) throw new Error("The text is empty.");
    const head = lines[0].split(",").map((s) => s.trim());
    if (head[0] !== "hand" || head.length !== 11) {
      throw new Error("The first line should be  hand,2,3,4,5,6,7,8,9,10,A");
    }
    const cols = UP_NAMES.map((u) => {
      const i = head.indexOf(u);
      if (i < 0) throw new Error(`The first line has no column ${u}.`);
      return i;
    });
    const rows = {};
    for (const line of lines.slice(1)) {
      const cells = line.split(",").map((s) => s.trim().toUpperCase());
      if (cells.length !== 11) throw new Error(`This line should have 11 entries: ${line}`);
      rows[cells[0]] = cells;
    }
    const chart = new Uint8Array(270);
    HAND_NAMES.forEach((h, r) => {
      const cells = rows[h];
      if (!cells) throw new Error(`There is no row for ${h}.`);
      cols.forEach((i, c) => {
        if (cells[i] !== "H" && cells[i] !== "S") {
          throw new Error(`${h} against ${UP_NAMES[c]} is "${cells[i]}"; it should be H or S.`);
        }
        chart[r * 10 + c] = cells[i] === "H" ? 1 : 0;
      });
    });
    return chart;
  }

  function chartToCsv(chart) {
    const out = ["hand," + UP_NAMES.join(",")];
    HAND_NAMES.forEach((h, r) => {
      const cells = [];
      for (let c = 0; c < 10; c++) cells.push(chart[r * 10 + c] ? "H" : "S");
      out.push(h + "," + cells.join(","));
    });
    return out.join("\n") + "\n";
  }

  // ------------------------------------------------------------ hands of cards
  // A card is {rank, suit}, with rank one of RANKS.

  function value(card) {
    return VALUES[RANKS.indexOf(card.rank)];
  }

  // {total, soft}. An ace counts 11 unless that would bust the hand; soft
  // means an ace is still counting 11.
  function handValue(cards) {
    let total = 0;
    let aces = 0;
    for (const c of cards) {
      total += value(c);
      if (c.rank === "A") aces++;
    }
    while (total > 21 && aces) {
      total -= 10;
      aces--;
    }
    return { total, soft: aces > 0 };
  }

  function isNatural(cards) {
    return cards.length === 2 && handValue(cards).total === 21;
  }

  function describe(cards) {
    const { total, soft } = handValue(cards);
    if (isNatural(cards)) return "blackjack";
    if (total > 21) return `bust with ${total}`;
    return `${soft ? "soft" : "hard"} ${total}`;
  }

  function upName(card) {
    return ["J", "Q", "K"].includes(card.rank) ? "10" : card.rank;
  }

  function against(card) {
    const n = upName(card);
    return n === "A" ? "against an ace" : `against ${n === "8" ? "an" : "a"} ${n}`;
  }

  // The chart's cell for these cards against this upcard, or -1 for soft 12
  // (two aces), which has no row and is always a hit.
  function cellOf(cards, upcard) {
    const { total, soft } = handValue(cards);
    if (soft && total === 12) return -1;
    return HAND_NAMES.indexOf((soft ? "S" : "H") + total) * 10 + UP_NAMES.indexOf(upName(upcard));
  }

  function advice(chart, cards, upcard) {
    const cell = cellOf(cards, upcard);
    return cell < 0 || chart[cell] ? "hit" : "stand";
  }

  function dealerHits(cards) {
    return handValue(cards).total < 17;
  }

  // What a $1 bet won: 1.5, 1, 0 or -1.
  function result(player, dealer) {
    if (isNatural(player)) return isNatural(dealer) ? 0 : 1.5;
    const p = handValue(player).total;
    const d = handValue(dealer).total;
    if (p > 21 || isNatural(dealer)) return -1;
    if (d > 21 || p > d) return 1;
    return p === d ? 0 : -1;
  }

  // ------------------------------------------------------------ random cards
  // A counter-based generator: card k of stream s in hand i is a hash of
  // (seed, i, s, k). A choice made in one hand doesn't change the cards of
  // any other hand, and the dealer's cards don't depend on how many cards
  // the player took. Two charts scored with the same seed see the same cards.

  function mix(x) {
    x = Math.imul(x ^ (x >>> 16), 0x7feb352d);
    x = Math.imul(x ^ (x >>> 15), 0x846ca68b);
    return (x ^ (x >>> 16)) >>> 0;
  }

  const DEALER = 0;
  const PLAYER = 1;
  const SLOTS = 64;
  const SLOT = new Uint32Array(2 * SLOTS);
  for (let i = 0; i < SLOT.length; i++) SLOT[i] = mix(i * 0x632be5ab + 0x2545f491);

  function handKey(base, i) {
    return mix(base ^ mix(i + 0x9e3779b9));
  }

  // The rank (0 to 12) of card k of a stream.
  function rankAt(key, stream, k) {
    const slot = k < SLOTS ? SLOT[stream * SLOTS + k] : mix(stream * 7919 + k * 104729);
    return Math.floor((mix(key ^ slot) * 13) / 4294967296);
  }

  function runBase(seed, label) {
    return mix((seed >>> 0) ^ mix(label + 0x85ebca6b));
  }

  // ------------------------------------------------------------ fast play
  // A hand as numbers: total, and soft as 0 or 1, packed as total + 32 * soft.

  function add(packed, card) {
    let total = packed & 31;
    let soft = packed >> 5;
    if (card === 11) {
      if (total + 11 <= 21) {
        total += 11;
        soft = 1;
      } else total += 1;
    } else total += card;
    if (total > 21 && soft) {
      total -= 10;
      soft = 0;
    }
    return total + 32 * soft;
  }

  function rowOf(total, soft) {
    return soft ? 18 + Math.min(Math.max(total - 13, 0), 8) : Math.min(Math.max(total - 4, 0), 17);
  }

  // The dealer from an upcard value: final total (22 for a bust) and
  // blackjack, packed as total + 32 * blackjack. Cards come from DEALER, from k.
  function dealerFinal(key, up, k) {
    let h = up + (up === 11 ? 32 : 0);
    h = add(h, VALUES[rankAt(key, DEALER, k++)]);
    const bj = (h & 31) === 21 ? 1 : 0;
    while ((h & 31) < 17) h = add(h, VALUES[rankAt(key, DEALER, k++)]);
    return Math.min(h & 31, 22) + 32 * bj;
  }

  // Hit by the chart until it says stand or the hand busts. Cards come from
  // PLAYER, from k.
  function followChart(chart, key, h, col, k) {
    for (;;) {
      const total = h & 31;
      if (total > 21) return h;
      const soft = h >> 5;
      const hit = soft && total === 12 ? 1 : chart[rowOf(total, soft) * 10 + col];
      if (!hit) return h;
      h = add(h, VALUES[rankAt(key, PLAYER, k++)]);
    }
  }

  function settle(p, d) {
    const dt = d & 31;
    if (p > 21 || d >> 5) return -1;
    if (dt > 21 || p > dt) return 1;
    return p === dt ? 0 : -1;
  }

  // One full hand by a chart: two cards each, the player follows the chart,
  // then the dealer plays.
  function fullHand(chart, key) {
    const upRank = rankAt(key, DEALER, 0);
    const up = VALUES[upRank];
    const col = up === 11 ? 9 : up - 2;
    let h = add(0, VALUES[rankAt(key, PLAYER, 0)]);
    h = add(h, VALUES[rankAt(key, PLAYER, 1)]);
    const d = dealerFinal(key, up, 1);
    if ((h & 31) === 21) return d >> 5 ? 0 : 1.5;
    h = followChart(chart, key, h, col, 2);
    return settle(h & 31, d);
  }

  // Score a chart over hands [from, from + count) of a run. With `other`, also
  // play it on the same cards and accumulate the difference chart - other.
  // acc holds n, sum, sumsq, dsum, dsumsq and is updated in place.
  function scoreChunk(chart, other, seed, from, count, acc) {
    const base = runBase(seed, 1);
    let sum = 0, sq = 0, dsum = 0, dsq = 0;
    for (let i = from; i < from + count; i++) {
      const key = handKey(base, i);
      const r = fullHand(chart, key);
      sum += r;
      sq += r * r;
      if (other) {
        const diff = r - fullHand(other, key);
        dsum += diff;
        dsq += diff * diff;
      }
    }
    acc.n += count;
    acc.sum += sum;
    acc.sumsq += sq;
    acc.dsum += dsum;
    acc.dsumsq += dsq;
    return acc;
  }

  function newAcc() {
    return { n: 0, sum: 0, sumsq: 0, dsum: 0, dsumsq: 0 };
  }

  function meanSe(n, sum, sumsq) {
    const mean = sum / n;
    return { mean, se: Math.sqrt(Math.max(sumsq / n - mean * mean, 0) / n) };
  }

  // One action in one cell, as blackjack.py's `cell` plays it: start from the
  // cell's total, stand, or take one card and then follow the chart; then
  // the dealer plays. Hit and stand use separate random cards.
  function cellChunk(chart, cell, action, seed, from, count, acc) {
    const { soft, total } = ROWS[Math.floor(cell / 10)];
    const col = cell % 10;
    const up = col === 9 ? 11 : col + 2;
    const base = runBase(seed, 1000 + 2 * cell + (action === "hit" ? 1 : 0));
    let sum = 0, sq = 0;
    for (let i = from; i < from + count; i++) {
      const key = handKey(base, i);
      let h = total + 32 * (soft ? 1 : 0);
      if (action === "hit") {
        h = add(h, VALUES[rankAt(key, PLAYER, 0)]);
        h = followChart(chart, key, h, col, 1);
      }
      const r = settle(h & 31, dealerFinal(key, up, 0));
      sum += r;
      sq += r * r;
    }
    acc.n += count;
    acc.sum += sum;
    acc.sumsq += sq;
    return acc;
  }

  // ------------------------------------------------------------ dealing

  function randomCard(random) {
    return {
      rank: RANKS[Math.floor(random() * 13)],
      suit: SUITS[Math.floor(random() * 4)],
    };
  }

  // Two cards that make the given hand (hard or soft total), chosen with the
  // chances real deals have, by dealing until a deal matches.
  function dealHand(random, soft, total) {
    for (;;) {
      const cards = [randomCard(random), randomCard(random)];
      const v = handValue(cards);
      if (v.soft === soft && v.total === total) return cards;
    }
  }

  // A card showing this upcard name ("10" is any of 10, J, Q, K).
  function cardShowing(random, name) {
    for (;;) {
      const c = randomCard(random);
      if (upName(c) === name) return c;
    }
  }

  // The hands a two-card deal can start a practice from.
  const PRACTICE_HANDS = HAND_NAMES.filter((h) => h !== "H21" && h !== "S21");

  const api = {
    RANKS, SUITS, VALUES, UP_NAMES, ROWS, HAND_NAMES, CHARTS, PRACTICE_HANDS,
    parseChart, chartToCsv, handValue, isNatural, describe, upName, against, cellOf,
    advice, dealerHits, result, scoreChunk, cellChunk, newAcc, meanSe,
    randomCard, dealHand, cardShowing,
    _internal: { mix, rankAt, handKey, runBase, add, fullHand, dealerFinal, followChart },
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.BJ = api;
})(this);
