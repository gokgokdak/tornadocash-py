var __getOwnPropNames = Object.getOwnPropertyNames;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};

// ../../big-integer/BigInteger.js
var require_BigInteger = __commonJS({
  "../../big-integer/BigInteger.js"(exports2, module2) {
    var bigInt3 = (function(undefined2) {
      "use strict";
      var BASE = 1e7, LOG_BASE = 7, MAX_INT = 9007199254740992, MAX_INT_ARR = smallToArray(MAX_INT), DEFAULT_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz";
      var supportsNativeBigInt = typeof BigInt === "function";
      function Integer(v, radix, alphabet, caseSensitive) {
        if (typeof v === "undefined") return Integer[0];
        if (typeof radix !== "undefined") return +radix === 10 && !alphabet ? parseValue(v) : parseBase(v, radix, alphabet, caseSensitive);
        return parseValue(v);
      }
      function BigInteger(value, sign) {
        this.value = value;
        this.sign = sign;
        this.isSmall = false;
      }
      BigInteger.prototype = Object.create(Integer.prototype);
      function SmallInteger(value) {
        this.value = value;
        this.sign = value < 0;
        this.isSmall = true;
      }
      SmallInteger.prototype = Object.create(Integer.prototype);
      function NativeBigInt(value) {
        this.value = value;
      }
      NativeBigInt.prototype = Object.create(Integer.prototype);
      function isPrecise(n) {
        return -MAX_INT < n && n < MAX_INT;
      }
      function smallToArray(n) {
        if (n < 1e7)
          return [n];
        if (n < 1e14)
          return [n % 1e7, Math.floor(n / 1e7)];
        return [n % 1e7, Math.floor(n / 1e7) % 1e7, Math.floor(n / 1e14)];
      }
      function arrayToSmall(arr) {
        trim(arr);
        var length = arr.length;
        if (length < 4 && compareAbs(arr, MAX_INT_ARR) < 0) {
          switch (length) {
            case 0:
              return 0;
            case 1:
              return arr[0];
            case 2:
              return arr[0] + arr[1] * BASE;
            default:
              return arr[0] + (arr[1] + arr[2] * BASE) * BASE;
          }
        }
        return arr;
      }
      function trim(v) {
        var i2 = v.length;
        while (v[--i2] === 0) ;
        v.length = i2 + 1;
      }
      function createArray(length) {
        var x = new Array(length);
        var i2 = -1;
        while (++i2 < length) {
          x[i2] = 0;
        }
        return x;
      }
      function truncate(n) {
        if (n > 0) return Math.floor(n);
        return Math.ceil(n);
      }
      function add(a, b) {
        var l_a = a.length, l_b = b.length, r = new Array(l_a), carry = 0, base = BASE, sum, i2;
        for (i2 = 0; i2 < l_b; i2++) {
          sum = a[i2] + b[i2] + carry;
          carry = sum >= base ? 1 : 0;
          r[i2] = sum - carry * base;
        }
        while (i2 < l_a) {
          sum = a[i2] + carry;
          carry = sum === base ? 1 : 0;
          r[i2++] = sum - carry * base;
        }
        if (carry > 0) r.push(carry);
        return r;
      }
      function addAny(a, b) {
        if (a.length >= b.length) return add(a, b);
        return add(b, a);
      }
      function addSmall(a, carry) {
        var l = a.length, r = new Array(l), base = BASE, sum, i2;
        for (i2 = 0; i2 < l; i2++) {
          sum = a[i2] - base + carry;
          carry = Math.floor(sum / base);
          r[i2] = sum - carry * base;
          carry += 1;
        }
        while (carry > 0) {
          r[i2++] = carry % base;
          carry = Math.floor(carry / base);
        }
        return r;
      }
      BigInteger.prototype.add = function(v) {
        var n = parseValue(v);
        if (this.sign !== n.sign) {
          return this.subtract(n.negate());
        }
        var a = this.value, b = n.value;
        if (n.isSmall) {
          return new BigInteger(addSmall(a, Math.abs(b)), this.sign);
        }
        return new BigInteger(addAny(a, b), this.sign);
      };
      BigInteger.prototype.plus = BigInteger.prototype.add;
      SmallInteger.prototype.add = function(v) {
        var n = parseValue(v);
        var a = this.value;
        if (a < 0 !== n.sign) {
          return this.subtract(n.negate());
        }
        var b = n.value;
        if (n.isSmall) {
          if (isPrecise(a + b)) return new SmallInteger(a + b);
          b = smallToArray(Math.abs(b));
        }
        return new BigInteger(addSmall(b, Math.abs(a)), a < 0);
      };
      SmallInteger.prototype.plus = SmallInteger.prototype.add;
      NativeBigInt.prototype.add = function(v) {
        return new NativeBigInt(this.value + parseValue(v).value);
      };
      NativeBigInt.prototype.plus = NativeBigInt.prototype.add;
      function subtract(a, b) {
        var a_l = a.length, b_l = b.length, r = new Array(a_l), borrow = 0, base = BASE, i2, difference;
        for (i2 = 0; i2 < b_l; i2++) {
          difference = a[i2] - borrow - b[i2];
          if (difference < 0) {
            difference += base;
            borrow = 1;
          } else borrow = 0;
          r[i2] = difference;
        }
        for (i2 = b_l; i2 < a_l; i2++) {
          difference = a[i2] - borrow;
          if (difference < 0) difference += base;
          else {
            r[i2++] = difference;
            break;
          }
          r[i2] = difference;
        }
        for (; i2 < a_l; i2++) {
          r[i2] = a[i2];
        }
        trim(r);
        return r;
      }
      function subtractAny(a, b, sign) {
        var value;
        if (compareAbs(a, b) >= 0) {
          value = subtract(a, b);
        } else {
          value = subtract(b, a);
          sign = !sign;
        }
        value = arrayToSmall(value);
        if (typeof value === "number") {
          if (sign) value = -value;
          return new SmallInteger(value);
        }
        return new BigInteger(value, sign);
      }
      function subtractSmall(a, b, sign) {
        var l = a.length, r = new Array(l), carry = -b, base = BASE, i2, difference;
        for (i2 = 0; i2 < l; i2++) {
          difference = a[i2] + carry;
          carry = Math.floor(difference / base);
          difference %= base;
          r[i2] = difference < 0 ? difference + base : difference;
        }
        r = arrayToSmall(r);
        if (typeof r === "number") {
          if (sign) r = -r;
          return new SmallInteger(r);
        }
        return new BigInteger(r, sign);
      }
      BigInteger.prototype.subtract = function(v) {
        var n = parseValue(v);
        if (this.sign !== n.sign) {
          return this.add(n.negate());
        }
        var a = this.value, b = n.value;
        if (n.isSmall)
          return subtractSmall(a, Math.abs(b), this.sign);
        return subtractAny(a, b, this.sign);
      };
      BigInteger.prototype.minus = BigInteger.prototype.subtract;
      SmallInteger.prototype.subtract = function(v) {
        var n = parseValue(v);
        var a = this.value;
        if (a < 0 !== n.sign) {
          return this.add(n.negate());
        }
        var b = n.value;
        if (n.isSmall) {
          return new SmallInteger(a - b);
        }
        return subtractSmall(b, Math.abs(a), a >= 0);
      };
      SmallInteger.prototype.minus = SmallInteger.prototype.subtract;
      NativeBigInt.prototype.subtract = function(v) {
        return new NativeBigInt(this.value - parseValue(v).value);
      };
      NativeBigInt.prototype.minus = NativeBigInt.prototype.subtract;
      BigInteger.prototype.negate = function() {
        return new BigInteger(this.value, !this.sign);
      };
      SmallInteger.prototype.negate = function() {
        var sign = this.sign;
        var small = new SmallInteger(-this.value);
        small.sign = !sign;
        return small;
      };
      NativeBigInt.prototype.negate = function() {
        return new NativeBigInt(-this.value);
      };
      BigInteger.prototype.abs = function() {
        return new BigInteger(this.value, false);
      };
      SmallInteger.prototype.abs = function() {
        return new SmallInteger(Math.abs(this.value));
      };
      NativeBigInt.prototype.abs = function() {
        return new NativeBigInt(this.value >= 0 ? this.value : -this.value);
      };
      function multiplyLong(a, b) {
        var a_l = a.length, b_l = b.length, l = a_l + b_l, r = createArray(l), base = BASE, product, carry, i2, a_i, b_j;
        for (i2 = 0; i2 < a_l; ++i2) {
          a_i = a[i2];
          for (var j = 0; j < b_l; ++j) {
            b_j = b[j];
            product = a_i * b_j + r[i2 + j];
            carry = Math.floor(product / base);
            r[i2 + j] = product - carry * base;
            r[i2 + j + 1] += carry;
          }
        }
        trim(r);
        return r;
      }
      function multiplySmall(a, b) {
        var l = a.length, r = new Array(l), base = BASE, carry = 0, product, i2;
        for (i2 = 0; i2 < l; i2++) {
          product = a[i2] * b + carry;
          carry = Math.floor(product / base);
          r[i2] = product - carry * base;
        }
        while (carry > 0) {
          r[i2++] = carry % base;
          carry = Math.floor(carry / base);
        }
        return r;
      }
      function shiftLeft(x, n) {
        var r = [];
        while (n-- > 0) r.push(0);
        return r.concat(x);
      }
      function multiplyKaratsuba(x, y) {
        var n = Math.max(x.length, y.length);
        if (n <= 30) return multiplyLong(x, y);
        n = Math.ceil(n / 2);
        var b = x.slice(n), a = x.slice(0, n), d = y.slice(n), c = y.slice(0, n);
        var ac = multiplyKaratsuba(a, c), bd = multiplyKaratsuba(b, d), abcd = multiplyKaratsuba(addAny(a, b), addAny(c, d));
        var product = addAny(addAny(ac, shiftLeft(subtract(subtract(abcd, ac), bd), n)), shiftLeft(bd, 2 * n));
        trim(product);
        return product;
      }
      function useKaratsuba(l1, l2) {
        return -0.012 * l1 - 0.012 * l2 + 15e-6 * l1 * l2 > 0;
      }
      BigInteger.prototype.multiply = function(v) {
        var n = parseValue(v), a = this.value, b = n.value, sign = this.sign !== n.sign, abs;
        if (n.isSmall) {
          if (b === 0) return Integer[0];
          if (b === 1) return this;
          if (b === -1) return this.negate();
          abs = Math.abs(b);
          if (abs < BASE) {
            return new BigInteger(multiplySmall(a, abs), sign);
          }
          b = smallToArray(abs);
        }
        if (useKaratsuba(a.length, b.length))
          return new BigInteger(multiplyKaratsuba(a, b), sign);
        return new BigInteger(multiplyLong(a, b), sign);
      };
      BigInteger.prototype.times = BigInteger.prototype.multiply;
      function multiplySmallAndArray(a, b, sign) {
        if (a < BASE) {
          return new BigInteger(multiplySmall(b, a), sign);
        }
        return new BigInteger(multiplyLong(b, smallToArray(a)), sign);
      }
      SmallInteger.prototype._multiplyBySmall = function(a) {
        if (isPrecise(a.value * this.value)) {
          return new SmallInteger(a.value * this.value);
        }
        return multiplySmallAndArray(Math.abs(a.value), smallToArray(Math.abs(this.value)), this.sign !== a.sign);
      };
      BigInteger.prototype._multiplyBySmall = function(a) {
        if (a.value === 0) return Integer[0];
        if (a.value === 1) return this;
        if (a.value === -1) return this.negate();
        return multiplySmallAndArray(Math.abs(a.value), this.value, this.sign !== a.sign);
      };
      SmallInteger.prototype.multiply = function(v) {
        return parseValue(v)._multiplyBySmall(this);
      };
      SmallInteger.prototype.times = SmallInteger.prototype.multiply;
      NativeBigInt.prototype.multiply = function(v) {
        return new NativeBigInt(this.value * parseValue(v).value);
      };
      NativeBigInt.prototype.times = NativeBigInt.prototype.multiply;
      function square(a) {
        var l = a.length, r = createArray(l + l), base = BASE, product, carry, i2, a_i, a_j;
        for (i2 = 0; i2 < l; i2++) {
          a_i = a[i2];
          carry = 0 - a_i * a_i;
          for (var j = i2; j < l; j++) {
            a_j = a[j];
            product = 2 * (a_i * a_j) + r[i2 + j] + carry;
            carry = Math.floor(product / base);
            r[i2 + j] = product - carry * base;
          }
          r[i2 + l] = carry;
        }
        trim(r);
        return r;
      }
      BigInteger.prototype.square = function() {
        return new BigInteger(square(this.value), false);
      };
      SmallInteger.prototype.square = function() {
        var value = this.value * this.value;
        if (isPrecise(value)) return new SmallInteger(value);
        return new BigInteger(square(smallToArray(Math.abs(this.value))), false);
      };
      NativeBigInt.prototype.square = function(v) {
        return new NativeBigInt(this.value * this.value);
      };
      function divMod1(a, b) {
        var a_l = a.length, b_l = b.length, base = BASE, result = createArray(b.length), divisorMostSignificantDigit = b[b_l - 1], lambda = Math.ceil(base / (2 * divisorMostSignificantDigit)), remainder = multiplySmall(a, lambda), divisor = multiplySmall(b, lambda), quotientDigit, shift, carry, borrow, i2, l, q;
        if (remainder.length <= a_l) remainder.push(0);
        divisor.push(0);
        divisorMostSignificantDigit = divisor[b_l - 1];
        for (shift = a_l - b_l; shift >= 0; shift--) {
          quotientDigit = base - 1;
          if (remainder[shift + b_l] !== divisorMostSignificantDigit) {
            quotientDigit = Math.floor((remainder[shift + b_l] * base + remainder[shift + b_l - 1]) / divisorMostSignificantDigit);
          }
          carry = 0;
          borrow = 0;
          l = divisor.length;
          for (i2 = 0; i2 < l; i2++) {
            carry += quotientDigit * divisor[i2];
            q = Math.floor(carry / base);
            borrow += remainder[shift + i2] - (carry - q * base);
            carry = q;
            if (borrow < 0) {
              remainder[shift + i2] = borrow + base;
              borrow = -1;
            } else {
              remainder[shift + i2] = borrow;
              borrow = 0;
            }
          }
          while (borrow !== 0) {
            quotientDigit -= 1;
            carry = 0;
            for (i2 = 0; i2 < l; i2++) {
              carry += remainder[shift + i2] - base + divisor[i2];
              if (carry < 0) {
                remainder[shift + i2] = carry + base;
                carry = 0;
              } else {
                remainder[shift + i2] = carry;
                carry = 1;
              }
            }
            borrow += carry;
          }
          result[shift] = quotientDigit;
        }
        remainder = divModSmall(remainder, lambda)[0];
        return [arrayToSmall(result), arrayToSmall(remainder)];
      }
      function divMod2(a, b) {
        var a_l = a.length, b_l = b.length, result = [], part = [], base = BASE, guess, xlen, highx, highy, check;
        while (a_l) {
          part.unshift(a[--a_l]);
          trim(part);
          if (compareAbs(part, b) < 0) {
            result.push(0);
            continue;
          }
          xlen = part.length;
          highx = part[xlen - 1] * base + part[xlen - 2];
          highy = b[b_l - 1] * base + b[b_l - 2];
          if (xlen > b_l) {
            highx = (highx + 1) * base;
          }
          guess = Math.ceil(highx / highy);
          do {
            check = multiplySmall(b, guess);
            if (compareAbs(check, part) <= 0) break;
            guess--;
          } while (guess);
          result.push(guess);
          part = subtract(part, check);
        }
        result.reverse();
        return [arrayToSmall(result), arrayToSmall(part)];
      }
      function divModSmall(value, lambda) {
        var length = value.length, quotient = createArray(length), base = BASE, i2, q, remainder, divisor;
        remainder = 0;
        for (i2 = length - 1; i2 >= 0; --i2) {
          divisor = remainder * base + value[i2];
          q = truncate(divisor / lambda);
          remainder = divisor - q * lambda;
          quotient[i2] = q | 0;
        }
        return [quotient, remainder | 0];
      }
      function divModAny(self, v) {
        var value, n = parseValue(v);
        if (supportsNativeBigInt) {
          return [new NativeBigInt(self.value / n.value), new NativeBigInt(self.value % n.value)];
        }
        var a = self.value, b = n.value;
        var quotient;
        if (b === 0) throw new Error("Cannot divide by zero");
        if (self.isSmall) {
          if (n.isSmall) {
            return [new SmallInteger(truncate(a / b)), new SmallInteger(a % b)];
          }
          return [Integer[0], self];
        }
        if (n.isSmall) {
          if (b === 1) return [self, Integer[0]];
          if (b == -1) return [self.negate(), Integer[0]];
          var abs = Math.abs(b);
          if (abs < BASE) {
            value = divModSmall(a, abs);
            quotient = arrayToSmall(value[0]);
            var remainder = value[1];
            if (self.sign) remainder = -remainder;
            if (typeof quotient === "number") {
              if (self.sign !== n.sign) quotient = -quotient;
              return [new SmallInteger(quotient), new SmallInteger(remainder)];
            }
            return [new BigInteger(quotient, self.sign !== n.sign), new SmallInteger(remainder)];
          }
          b = smallToArray(abs);
        }
        var comparison = compareAbs(a, b);
        if (comparison === -1) return [Integer[0], self];
        if (comparison === 0) return [Integer[self.sign === n.sign ? 1 : -1], Integer[0]];
        if (a.length + b.length <= 200)
          value = divMod1(a, b);
        else value = divMod2(a, b);
        quotient = value[0];
        var qSign = self.sign !== n.sign, mod = value[1], mSign = self.sign;
        if (typeof quotient === "number") {
          if (qSign) quotient = -quotient;
          quotient = new SmallInteger(quotient);
        } else quotient = new BigInteger(quotient, qSign);
        if (typeof mod === "number") {
          if (mSign) mod = -mod;
          mod = new SmallInteger(mod);
        } else mod = new BigInteger(mod, mSign);
        return [quotient, mod];
      }
      BigInteger.prototype.divmod = function(v) {
        var result = divModAny(this, v);
        return {
          quotient: result[0],
          remainder: result[1]
        };
      };
      NativeBigInt.prototype.divmod = SmallInteger.prototype.divmod = BigInteger.prototype.divmod;
      BigInteger.prototype.divide = function(v) {
        return divModAny(this, v)[0];
      };
      NativeBigInt.prototype.over = NativeBigInt.prototype.divide = function(v) {
        return new NativeBigInt(this.value / parseValue(v).value);
      };
      SmallInteger.prototype.over = SmallInteger.prototype.divide = BigInteger.prototype.over = BigInteger.prototype.divide;
      BigInteger.prototype.mod = function(v) {
        return divModAny(this, v)[1];
      };
      NativeBigInt.prototype.mod = NativeBigInt.prototype.remainder = function(v) {
        return new NativeBigInt(this.value % parseValue(v).value);
      };
      SmallInteger.prototype.remainder = SmallInteger.prototype.mod = BigInteger.prototype.remainder = BigInteger.prototype.mod;
      BigInteger.prototype.pow = function(v) {
        var n = parseValue(v), a = this.value, b = n.value, value, x, y;
        if (b === 0) return Integer[1];
        if (a === 0) return Integer[0];
        if (a === 1) return Integer[1];
        if (a === -1) return n.isEven() ? Integer[1] : Integer[-1];
        if (n.sign) {
          return Integer[0];
        }
        if (!n.isSmall) throw new Error("The exponent " + n.toString() + " is too large.");
        if (this.isSmall) {
          if (isPrecise(value = Math.pow(a, b)))
            return new SmallInteger(truncate(value));
        }
        x = this;
        y = Integer[1];
        while (true) {
          if (b & true) {
            y = y.times(x);
            --b;
          }
          if (b === 0) break;
          b /= 2;
          x = x.square();
        }
        return y;
      };
      SmallInteger.prototype.pow = BigInteger.prototype.pow;
      NativeBigInt.prototype.pow = function(v) {
        var n = parseValue(v);
        var a = this.value, b = n.value;
        var _0 = BigInt(0), _1 = BigInt(1), _2 = BigInt(2);
        if (b === _0) return Integer[1];
        if (a === _0) return Integer[0];
        if (a === _1) return Integer[1];
        if (a === BigInt(-1)) return n.isEven() ? Integer[1] : Integer[-1];
        if (n.isNegative()) return new NativeBigInt(_0);
        var x = this;
        var y = Integer[1];
        while (true) {
          if ((b & _1) === _1) {
            y = y.times(x);
            --b;
          }
          if (b === _0) break;
          b /= _2;
          x = x.square();
        }
        return y;
      };
      BigInteger.prototype.modPow = function(exp, mod) {
        exp = parseValue(exp);
        mod = parseValue(mod);
        if (mod.isZero()) throw new Error("Cannot take modPow with modulus 0");
        var r = Integer[1], base = this.mod(mod);
        if (exp.isNegative()) {
          exp = exp.multiply(Integer[-1]);
          base = base.modInv(mod);
        }
        while (exp.isPositive()) {
          if (base.isZero()) return Integer[0];
          if (exp.isOdd()) r = r.multiply(base).mod(mod);
          exp = exp.divide(2);
          base = base.square().mod(mod);
        }
        return r;
      };
      NativeBigInt.prototype.modPow = SmallInteger.prototype.modPow = BigInteger.prototype.modPow;
      function compareAbs(a, b) {
        if (a.length !== b.length) {
          return a.length > b.length ? 1 : -1;
        }
        for (var i2 = a.length - 1; i2 >= 0; i2--) {
          if (a[i2] !== b[i2]) return a[i2] > b[i2] ? 1 : -1;
        }
        return 0;
      }
      BigInteger.prototype.compareAbs = function(v) {
        var n = parseValue(v), a = this.value, b = n.value;
        if (n.isSmall) return 1;
        return compareAbs(a, b);
      };
      SmallInteger.prototype.compareAbs = function(v) {
        var n = parseValue(v), a = Math.abs(this.value), b = n.value;
        if (n.isSmall) {
          b = Math.abs(b);
          return a === b ? 0 : a > b ? 1 : -1;
        }
        return -1;
      };
      NativeBigInt.prototype.compareAbs = function(v) {
        var a = this.value;
        var b = parseValue(v).value;
        a = a >= 0 ? a : -a;
        b = b >= 0 ? b : -b;
        return a === b ? 0 : a > b ? 1 : -1;
      };
      BigInteger.prototype.compare = function(v) {
        if (v === Infinity) {
          return -1;
        }
        if (v === -Infinity) {
          return 1;
        }
        var n = parseValue(v), a = this.value, b = n.value;
        if (this.sign !== n.sign) {
          return n.sign ? 1 : -1;
        }
        if (n.isSmall) {
          return this.sign ? -1 : 1;
        }
        return compareAbs(a, b) * (this.sign ? -1 : 1);
      };
      BigInteger.prototype.compareTo = BigInteger.prototype.compare;
      SmallInteger.prototype.compare = function(v) {
        if (v === Infinity) {
          return -1;
        }
        if (v === -Infinity) {
          return 1;
        }
        var n = parseValue(v), a = this.value, b = n.value;
        if (n.isSmall) {
          return a == b ? 0 : a > b ? 1 : -1;
        }
        if (a < 0 !== n.sign) {
          return a < 0 ? -1 : 1;
        }
        return a < 0 ? 1 : -1;
      };
      SmallInteger.prototype.compareTo = SmallInteger.prototype.compare;
      NativeBigInt.prototype.compare = function(v) {
        if (v === Infinity) {
          return -1;
        }
        if (v === -Infinity) {
          return 1;
        }
        var a = this.value;
        var b = parseValue(v).value;
        return a === b ? 0 : a > b ? 1 : -1;
      };
      NativeBigInt.prototype.compareTo = NativeBigInt.prototype.compare;
      BigInteger.prototype.equals = function(v) {
        return this.compare(v) === 0;
      };
      NativeBigInt.prototype.eq = NativeBigInt.prototype.equals = SmallInteger.prototype.eq = SmallInteger.prototype.equals = BigInteger.prototype.eq = BigInteger.prototype.equals;
      BigInteger.prototype.notEquals = function(v) {
        return this.compare(v) !== 0;
      };
      NativeBigInt.prototype.neq = NativeBigInt.prototype.notEquals = SmallInteger.prototype.neq = SmallInteger.prototype.notEquals = BigInteger.prototype.neq = BigInteger.prototype.notEquals;
      BigInteger.prototype.greater = function(v) {
        return this.compare(v) > 0;
      };
      NativeBigInt.prototype.gt = NativeBigInt.prototype.greater = SmallInteger.prototype.gt = SmallInteger.prototype.greater = BigInteger.prototype.gt = BigInteger.prototype.greater;
      BigInteger.prototype.lesser = function(v) {
        return this.compare(v) < 0;
      };
      NativeBigInt.prototype.lt = NativeBigInt.prototype.lesser = SmallInteger.prototype.lt = SmallInteger.prototype.lesser = BigInteger.prototype.lt = BigInteger.prototype.lesser;
      BigInteger.prototype.greaterOrEquals = function(v) {
        return this.compare(v) >= 0;
      };
      NativeBigInt.prototype.geq = NativeBigInt.prototype.greaterOrEquals = SmallInteger.prototype.geq = SmallInteger.prototype.greaterOrEquals = BigInteger.prototype.geq = BigInteger.prototype.greaterOrEquals;
      BigInteger.prototype.lesserOrEquals = function(v) {
        return this.compare(v) <= 0;
      };
      NativeBigInt.prototype.leq = NativeBigInt.prototype.lesserOrEquals = SmallInteger.prototype.leq = SmallInteger.prototype.lesserOrEquals = BigInteger.prototype.leq = BigInteger.prototype.lesserOrEquals;
      BigInteger.prototype.isEven = function() {
        return (this.value[0] & 1) === 0;
      };
      SmallInteger.prototype.isEven = function() {
        return (this.value & 1) === 0;
      };
      NativeBigInt.prototype.isEven = function() {
        return (this.value & BigInt(1)) === BigInt(0);
      };
      BigInteger.prototype.isOdd = function() {
        return (this.value[0] & 1) === 1;
      };
      SmallInteger.prototype.isOdd = function() {
        return (this.value & 1) === 1;
      };
      NativeBigInt.prototype.isOdd = function() {
        return (this.value & BigInt(1)) === BigInt(1);
      };
      BigInteger.prototype.isPositive = function() {
        return !this.sign;
      };
      SmallInteger.prototype.isPositive = function() {
        return this.value > 0;
      };
      NativeBigInt.prototype.isPositive = SmallInteger.prototype.isPositive;
      BigInteger.prototype.isNegative = function() {
        return this.sign;
      };
      SmallInteger.prototype.isNegative = function() {
        return this.value < 0;
      };
      NativeBigInt.prototype.isNegative = SmallInteger.prototype.isNegative;
      BigInteger.prototype.isUnit = function() {
        return false;
      };
      SmallInteger.prototype.isUnit = function() {
        return Math.abs(this.value) === 1;
      };
      NativeBigInt.prototype.isUnit = function() {
        return this.abs().value === BigInt(1);
      };
      BigInteger.prototype.isZero = function() {
        return false;
      };
      SmallInteger.prototype.isZero = function() {
        return this.value === 0;
      };
      NativeBigInt.prototype.isZero = function() {
        return this.value === BigInt(0);
      };
      BigInteger.prototype.isDivisibleBy = function(v) {
        var n = parseValue(v);
        if (n.isZero()) return false;
        if (n.isUnit()) return true;
        if (n.compareAbs(2) === 0) return this.isEven();
        return this.mod(n).isZero();
      };
      NativeBigInt.prototype.isDivisibleBy = SmallInteger.prototype.isDivisibleBy = BigInteger.prototype.isDivisibleBy;
      function isBasicPrime(v) {
        var n = v.abs();
        if (n.isUnit()) return false;
        if (n.equals(2) || n.equals(3) || n.equals(5)) return true;
        if (n.isEven() || n.isDivisibleBy(3) || n.isDivisibleBy(5)) return false;
        if (n.lesser(49)) return true;
      }
      function millerRabinTest(n, a) {
        var nPrev = n.prev(), b = nPrev, r = 0, d, t2, i2, x;
        while (b.isEven()) b = b.divide(2), r++;
        next: for (i2 = 0; i2 < a.length; i2++) {
          if (n.lesser(a[i2])) continue;
          x = bigInt3(a[i2]).modPow(b, n);
          if (x.isUnit() || x.equals(nPrev)) continue;
          for (d = r - 1; d != 0; d--) {
            x = x.square().mod(n);
            if (x.isUnit()) return false;
            if (x.equals(nPrev)) continue next;
          }
          return false;
        }
        return true;
      }
      BigInteger.prototype.isPrime = function(strict) {
        var isPrime = isBasicPrime(this);
        if (isPrime !== undefined2) return isPrime;
        var n = this.abs();
        var bits = n.bitLength();
        if (bits <= 64)
          return millerRabinTest(n, [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]);
        var logN = Math.log(2) * bits.toJSNumber();
        var t2 = Math.ceil(strict === true ? 2 * Math.pow(logN, 2) : logN);
        for (var a = [], i2 = 0; i2 < t2; i2++) {
          a.push(bigInt3(i2 + 2));
        }
        return millerRabinTest(n, a);
      };
      NativeBigInt.prototype.isPrime = SmallInteger.prototype.isPrime = BigInteger.prototype.isPrime;
      BigInteger.prototype.isProbablePrime = function(iterations, rng) {
        var isPrime = isBasicPrime(this);
        if (isPrime !== undefined2) return isPrime;
        var n = this.abs();
        var t2 = iterations === undefined2 ? 5 : iterations;
        for (var a = [], i2 = 0; i2 < t2; i2++) {
          a.push(bigInt3.randBetween(2, n.minus(2), rng));
        }
        return millerRabinTest(n, a);
      };
      NativeBigInt.prototype.isProbablePrime = SmallInteger.prototype.isProbablePrime = BigInteger.prototype.isProbablePrime;
      BigInteger.prototype.modInv = function(n) {
        var t2 = bigInt3.zero, newT = bigInt3.one, r = parseValue(n), newR = this.abs(), q, lastT, lastR;
        while (!newR.isZero()) {
          q = r.divide(newR);
          lastT = t2;
          lastR = r;
          t2 = newT;
          r = newR;
          newT = lastT.subtract(q.multiply(newT));
          newR = lastR.subtract(q.multiply(newR));
        }
        if (!r.isUnit()) throw new Error(this.toString() + " and " + n.toString() + " are not co-prime");
        if (t2.compare(0) === -1) {
          t2 = t2.add(n);
        }
        if (this.isNegative()) {
          return t2.negate();
        }
        return t2;
      };
      NativeBigInt.prototype.modInv = SmallInteger.prototype.modInv = BigInteger.prototype.modInv;
      BigInteger.prototype.next = function() {
        var value = this.value;
        if (this.sign) {
          return subtractSmall(value, 1, this.sign);
        }
        return new BigInteger(addSmall(value, 1), this.sign);
      };
      SmallInteger.prototype.next = function() {
        var value = this.value;
        if (value + 1 < MAX_INT) return new SmallInteger(value + 1);
        return new BigInteger(MAX_INT_ARR, false);
      };
      NativeBigInt.prototype.next = function() {
        return new NativeBigInt(this.value + BigInt(1));
      };
      BigInteger.prototype.prev = function() {
        var value = this.value;
        if (this.sign) {
          return new BigInteger(addSmall(value, 1), true);
        }
        return subtractSmall(value, 1, this.sign);
      };
      SmallInteger.prototype.prev = function() {
        var value = this.value;
        if (value - 1 > -MAX_INT) return new SmallInteger(value - 1);
        return new BigInteger(MAX_INT_ARR, true);
      };
      NativeBigInt.prototype.prev = function() {
        return new NativeBigInt(this.value - BigInt(1));
      };
      var powersOfTwo = [1];
      while (2 * powersOfTwo[powersOfTwo.length - 1] <= BASE) powersOfTwo.push(2 * powersOfTwo[powersOfTwo.length - 1]);
      var powers2Length = powersOfTwo.length, highestPower2 = powersOfTwo[powers2Length - 1];
      function shift_isSmall(n) {
        return Math.abs(n) <= BASE;
      }
      BigInteger.prototype.shiftLeft = function(v) {
        var n = parseValue(v).toJSNumber();
        if (!shift_isSmall(n)) {
          throw new Error(String(n) + " is too large for shifting.");
        }
        if (n < 0) return this.shiftRight(-n);
        var result = this;
        if (result.isZero()) return result;
        while (n >= powers2Length) {
          result = result.multiply(highestPower2);
          n -= powers2Length - 1;
        }
        return result.multiply(powersOfTwo[n]);
      };
      NativeBigInt.prototype.shiftLeft = SmallInteger.prototype.shiftLeft = BigInteger.prototype.shiftLeft;
      BigInteger.prototype.shiftRight = function(v) {
        var remQuo;
        var n = parseValue(v).toJSNumber();
        if (!shift_isSmall(n)) {
          throw new Error(String(n) + " is too large for shifting.");
        }
        if (n < 0) return this.shiftLeft(-n);
        var result = this;
        while (n >= powers2Length) {
          if (result.isZero() || result.isNegative() && result.isUnit()) return result;
          remQuo = divModAny(result, highestPower2);
          result = remQuo[1].isNegative() ? remQuo[0].prev() : remQuo[0];
          n -= powers2Length - 1;
        }
        remQuo = divModAny(result, powersOfTwo[n]);
        return remQuo[1].isNegative() ? remQuo[0].prev() : remQuo[0];
      };
      NativeBigInt.prototype.shiftRight = SmallInteger.prototype.shiftRight = BigInteger.prototype.shiftRight;
      function bitwise(x, y, fn) {
        y = parseValue(y);
        var xSign = x.isNegative(), ySign = y.isNegative();
        var xRem = xSign ? x.not() : x, yRem = ySign ? y.not() : y;
        var xDigit = 0, yDigit = 0;
        var xDivMod = null, yDivMod = null;
        var result = [];
        while (!xRem.isZero() || !yRem.isZero()) {
          xDivMod = divModAny(xRem, highestPower2);
          xDigit = xDivMod[1].toJSNumber();
          if (xSign) {
            xDigit = highestPower2 - 1 - xDigit;
          }
          yDivMod = divModAny(yRem, highestPower2);
          yDigit = yDivMod[1].toJSNumber();
          if (ySign) {
            yDigit = highestPower2 - 1 - yDigit;
          }
          xRem = xDivMod[0];
          yRem = yDivMod[0];
          result.push(fn(xDigit, yDigit));
        }
        var sum = fn(xSign ? 1 : 0, ySign ? 1 : 0) !== 0 ? bigInt3(-1) : bigInt3(0);
        for (var i2 = result.length - 1; i2 >= 0; i2 -= 1) {
          sum = sum.multiply(highestPower2).add(bigInt3(result[i2]));
        }
        return sum;
      }
      BigInteger.prototype.not = function() {
        return this.negate().prev();
      };
      NativeBigInt.prototype.not = SmallInteger.prototype.not = BigInteger.prototype.not;
      BigInteger.prototype.and = function(n) {
        return bitwise(this, n, function(a, b) {
          return a & b;
        });
      };
      NativeBigInt.prototype.and = SmallInteger.prototype.and = BigInteger.prototype.and;
      BigInteger.prototype.or = function(n) {
        return bitwise(this, n, function(a, b) {
          return a | b;
        });
      };
      NativeBigInt.prototype.or = SmallInteger.prototype.or = BigInteger.prototype.or;
      BigInteger.prototype.xor = function(n) {
        return bitwise(this, n, function(a, b) {
          return a ^ b;
        });
      };
      NativeBigInt.prototype.xor = SmallInteger.prototype.xor = BigInteger.prototype.xor;
      var LOBMASK_I = 1 << 30, LOBMASK_BI = (BASE & -BASE) * (BASE & -BASE) | LOBMASK_I;
      function roughLOB(n) {
        var v = n.value, x = typeof v === "number" ? v | LOBMASK_I : typeof v === "bigint" ? v | BigInt(LOBMASK_I) : v[0] + v[1] * BASE | LOBMASK_BI;
        return x & -x;
      }
      function integerLogarithm(value, base) {
        if (base.compareTo(value) <= 0) {
          var tmp = integerLogarithm(value, base.square(base));
          var p = tmp.p;
          var e = tmp.e;
          var t2 = p.multiply(base);
          return t2.compareTo(value) <= 0 ? { p: t2, e: e * 2 + 1 } : { p, e: e * 2 };
        }
        return { p: bigInt3(1), e: 0 };
      }
      BigInteger.prototype.bitLength = function() {
        var n = this;
        if (n.compareTo(bigInt3(0)) < 0) {
          n = n.negate().subtract(bigInt3(1));
        }
        if (n.compareTo(bigInt3(0)) === 0) {
          return bigInt3(0);
        }
        return bigInt3(integerLogarithm(n, bigInt3(2)).e).add(bigInt3(1));
      };
      NativeBigInt.prototype.bitLength = SmallInteger.prototype.bitLength = BigInteger.prototype.bitLength;
      function max(a, b) {
        a = parseValue(a);
        b = parseValue(b);
        return a.greater(b) ? a : b;
      }
      function min(a, b) {
        a = parseValue(a);
        b = parseValue(b);
        return a.lesser(b) ? a : b;
      }
      function gcd(a, b) {
        a = parseValue(a).abs();
        b = parseValue(b).abs();
        if (a.equals(b)) return a;
        if (a.isZero()) return b;
        if (b.isZero()) return a;
        var c = Integer[1], d, t2;
        while (a.isEven() && b.isEven()) {
          d = min(roughLOB(a), roughLOB(b));
          a = a.divide(d);
          b = b.divide(d);
          c = c.multiply(d);
        }
        while (a.isEven()) {
          a = a.divide(roughLOB(a));
        }
        do {
          while (b.isEven()) {
            b = b.divide(roughLOB(b));
          }
          if (a.greater(b)) {
            t2 = b;
            b = a;
            a = t2;
          }
          b = b.subtract(a);
        } while (!b.isZero());
        return c.isUnit() ? a : a.multiply(c);
      }
      function lcm(a, b) {
        a = parseValue(a).abs();
        b = parseValue(b).abs();
        return a.divide(gcd(a, b)).multiply(b);
      }
      function randBetween(a, b, rng) {
        a = parseValue(a);
        b = parseValue(b);
        var usedRNG = rng || Math.random;
        var low = min(a, b), high = max(a, b);
        var range = high.subtract(low).add(1);
        if (range.isSmall) return low.add(Math.floor(usedRNG() * range));
        var digits = toBase(range, BASE).value;
        var result = [], restricted = true;
        for (var i2 = 0; i2 < digits.length; i2++) {
          var top = restricted ? digits[i2] : BASE;
          var digit = truncate(usedRNG() * top);
          result.push(digit);
          if (digit < top) restricted = false;
        }
        return low.add(Integer.fromArray(result, BASE, false));
      }
      var parseBase = function(text, base, alphabet, caseSensitive) {
        alphabet = alphabet || DEFAULT_ALPHABET;
        text = String(text);
        if (!caseSensitive) {
          text = text.toLowerCase();
          alphabet = alphabet.toLowerCase();
        }
        var length = text.length;
        var i2;
        var absBase = Math.abs(base);
        var alphabetValues = {};
        for (i2 = 0; i2 < alphabet.length; i2++) {
          alphabetValues[alphabet[i2]] = i2;
        }
        for (i2 = 0; i2 < length; i2++) {
          var c = text[i2];
          if (c === "-") continue;
          if (c in alphabetValues) {
            if (alphabetValues[c] >= absBase) {
              if (c === "1" && absBase === 1) continue;
              throw new Error(c + " is not a valid digit in base " + base + ".");
            }
          }
        }
        base = parseValue(base);
        var digits = [];
        var isNegative = text[0] === "-";
        for (i2 = isNegative ? 1 : 0; i2 < text.length; i2++) {
          var c = text[i2];
          if (c in alphabetValues) digits.push(parseValue(alphabetValues[c]));
          else if (c === "<") {
            var start = i2;
            do {
              i2++;
            } while (text[i2] !== ">" && i2 < text.length);
            digits.push(parseValue(text.slice(start + 1, i2)));
          } else throw new Error(c + " is not a valid character");
        }
        return parseBaseFromArray(digits, base, isNegative);
      };
      function parseBaseFromArray(digits, base, isNegative) {
        var val = Integer[0], pow = Integer[1], i2;
        for (i2 = digits.length - 1; i2 >= 0; i2--) {
          val = val.add(digits[i2].times(pow));
          pow = pow.times(base);
        }
        return isNegative ? val.negate() : val;
      }
      function stringify(digit, alphabet) {
        alphabet = alphabet || DEFAULT_ALPHABET;
        if (digit < alphabet.length) {
          return alphabet[digit];
        }
        return "<" + digit + ">";
      }
      function toBase(n, base) {
        base = bigInt3(base);
        if (base.isZero()) {
          if (n.isZero()) return { value: [0], isNegative: false };
          throw new Error("Cannot convert nonzero numbers to base 0.");
        }
        if (base.equals(-1)) {
          if (n.isZero()) return { value: [0], isNegative: false };
          if (n.isNegative())
            return {
              value: [].concat.apply(
                [],
                Array.apply(null, Array(-n.toJSNumber())).map(Array.prototype.valueOf, [1, 0])
              ),
              isNegative: false
            };
          var arr = Array.apply(null, Array(n.toJSNumber() - 1)).map(Array.prototype.valueOf, [0, 1]);
          arr.unshift([1]);
          return {
            value: [].concat.apply([], arr),
            isNegative: false
          };
        }
        var neg = false;
        if (n.isNegative() && base.isPositive()) {
          neg = true;
          n = n.abs();
        }
        if (base.isUnit()) {
          if (n.isZero()) return { value: [0], isNegative: false };
          return {
            value: Array.apply(null, Array(n.toJSNumber())).map(Number.prototype.valueOf, 1),
            isNegative: neg
          };
        }
        var out = [];
        var left = n, divmod;
        while (left.isNegative() || left.compareAbs(base) >= 0) {
          divmod = left.divmod(base);
          left = divmod.quotient;
          var digit = divmod.remainder;
          if (digit.isNegative()) {
            digit = base.minus(digit).abs();
            left = left.next();
          }
          out.push(digit.toJSNumber());
        }
        out.push(left.toJSNumber());
        return { value: out.reverse(), isNegative: neg };
      }
      function toBaseString(n, base, alphabet) {
        var arr = toBase(n, base);
        return (arr.isNegative ? "-" : "") + arr.value.map(function(x) {
          return stringify(x, alphabet);
        }).join("");
      }
      BigInteger.prototype.toArray = function(radix) {
        return toBase(this, radix);
      };
      SmallInteger.prototype.toArray = function(radix) {
        return toBase(this, radix);
      };
      NativeBigInt.prototype.toArray = function(radix) {
        return toBase(this, radix);
      };
      BigInteger.prototype.toString = function(radix, alphabet) {
        if (radix === undefined2) radix = 10;
        if (radix !== 10) return toBaseString(this, radix, alphabet);
        var v = this.value, l = v.length, str = String(v[--l]), zeros = "0000000", digit;
        while (--l >= 0) {
          digit = String(v[l]);
          str += zeros.slice(digit.length) + digit;
        }
        var sign = this.sign ? "-" : "";
        return sign + str;
      };
      SmallInteger.prototype.toString = function(radix, alphabet) {
        if (radix === undefined2) radix = 10;
        if (radix != 10) return toBaseString(this, radix, alphabet);
        return String(this.value);
      };
      NativeBigInt.prototype.toString = SmallInteger.prototype.toString;
      NativeBigInt.prototype.toJSON = BigInteger.prototype.toJSON = SmallInteger.prototype.toJSON = function() {
        return this.toString();
      };
      BigInteger.prototype.valueOf = function() {
        return parseInt(this.toString(), 10);
      };
      BigInteger.prototype.toJSNumber = BigInteger.prototype.valueOf;
      SmallInteger.prototype.valueOf = function() {
        return this.value;
      };
      SmallInteger.prototype.toJSNumber = SmallInteger.prototype.valueOf;
      NativeBigInt.prototype.valueOf = NativeBigInt.prototype.toJSNumber = function() {
        return parseInt(this.toString(), 10);
      };
      function parseStringValue(v) {
        if (isPrecise(+v)) {
          var x = +v;
          if (x === truncate(x))
            return supportsNativeBigInt ? new NativeBigInt(BigInt(x)) : new SmallInteger(x);
          throw new Error("Invalid integer: " + v);
        }
        var sign = v[0] === "-";
        if (sign) v = v.slice(1);
        var split = v.split(/e/i);
        if (split.length > 2) throw new Error("Invalid integer: " + split.join("e"));
        if (split.length === 2) {
          var exp = split[1];
          if (exp[0] === "+") exp = exp.slice(1);
          exp = +exp;
          if (exp !== truncate(exp) || !isPrecise(exp)) throw new Error("Invalid integer: " + exp + " is not a valid exponent.");
          var text = split[0];
          var decimalPlace = text.indexOf(".");
          if (decimalPlace >= 0) {
            exp -= text.length - decimalPlace - 1;
            text = text.slice(0, decimalPlace) + text.slice(decimalPlace + 1);
          }
          if (exp < 0) throw new Error("Cannot include negative exponent part for integers");
          text += new Array(exp + 1).join("0");
          v = text;
        }
        var isValid = /^([0-9][0-9]*)$/.test(v);
        if (!isValid) throw new Error("Invalid integer: " + v);
        if (supportsNativeBigInt) {
          return new NativeBigInt(BigInt(sign ? "-" + v : v));
        }
        var r = [], max2 = v.length, l = LOG_BASE, min2 = max2 - l;
        while (max2 > 0) {
          r.push(+v.slice(min2, max2));
          min2 -= l;
          if (min2 < 0) min2 = 0;
          max2 -= l;
        }
        trim(r);
        return new BigInteger(r, sign);
      }
      function parseNumberValue(v) {
        if (supportsNativeBigInt) {
          return new NativeBigInt(BigInt(v));
        }
        if (isPrecise(v)) {
          if (v !== truncate(v)) throw new Error(v + " is not an integer.");
          return new SmallInteger(v);
        }
        return parseStringValue(v.toString());
      }
      function parseValue(v) {
        if (typeof v === "number") {
          return parseNumberValue(v);
        }
        if (typeof v === "string") {
          return parseStringValue(v);
        }
        if (typeof v === "bigint") {
          return new NativeBigInt(v);
        }
        return v;
      }
      for (var i = 0; i < 1e3; i++) {
        Integer[i] = parseValue(i);
        if (i > 0) Integer[-i] = parseValue(-i);
      }
      Integer.one = Integer[1];
      Integer.zero = Integer[0];
      Integer.minusOne = Integer[-1];
      Integer.max = max;
      Integer.min = min;
      Integer.gcd = gcd;
      Integer.lcm = lcm;
      Integer.isInstance = function(x) {
        return x instanceof BigInteger || x instanceof SmallInteger || x instanceof NativeBigInt;
      };
      Integer.randBetween = randBetween;
      Integer.fromArray = function(digits, base, isNegative) {
        return parseBaseFromArray(digits.map(parseValue), parseValue(base || 10), isNegative);
      };
      return Integer;
    })();
    if (typeof module2 !== "undefined" && module2.hasOwnProperty("exports")) {
      module2.exports = bigInt3;
    }
    if (typeof define === "function" && define.amd) {
      define(function() {
        return bigInt3;
      });
    }
  }
});

// ../build/groth16_wasm.js
var require_groth16_wasm = __commonJS({
  "../build/groth16_wasm.js"(exports2) {
    exports2.code = new Buffer.from("AGFzbQEAAAABPApgAn9/AGABfwBgAX8Bf2ACf38Bf2ADf39/AX9gA39/fwBgA39+fwBgAn9+AGAEf39/fwBgBX9/f39/AAIQAQNlbnYGbWVtb3J5AgDoBwNsawABAgEDAwQEBQUGBwgFBQUAAAUFAAAAAQUFAAAFBQAAAAEFAAIBAAAFAAUAAAAIAQIAAgUICQgABQkDAAUFBQUAAgUFCAAIAgEBAAUFBQAAAAMAAgEAAAUABQAAAAgBAgACBQgJCAAFCQgIB8gJYghpbnRfY29weQAACGludF96ZXJvAAEHaW50X29uZQADCmludF9pc1plcm8AAgZpbnRfZXEABAdpbnRfZ3RlAAUHaW50X2FkZAAGB2ludF9zdWIABwppbnRfbXVsT2xkAAkHaW50X211bAAIB2ludF9kaXYADA5pbnRfaW52ZXJzZU1vZAANB2YxbV9hZGQADgdmMW1fc3ViAA8HZjFtX25lZwAQC2YxbV9tUmVkdWN0ABEHZjFtX211bAASCmYxbV9tdWxPbGQAExJmMW1fZnJvbU1vbnRnb21lcnkAFRBmMW1fdG9Nb250Z29tZXJ5ABQLZjFtX2ludmVyc2UAFghmMW1fY29weQAACGYxbV96ZXJvAAEKZjFtX2lzWmVybwACBmYxbV9lcQAEB2YxbV9vbmUAFwdmcm1fYWRkABgHZnJtX3N1YgAZB2ZybV9uZWcAGgtmcm1fbVJlZHVjdAAbB2ZybV9tdWwAHApmcm1fbXVsT2xkAB0SZnJtX2Zyb21Nb250Z29tZXJ5AB8QZnJtX3RvTW9udGdvbWVyeQAeC2ZybV9pbnZlcnNlACAIZnJtX2NvcHkAAAhmcm1femVybwABCmZybV9pc1plcm8AAgZmcm1fZXEABAdmcm1fb25lACEGZnJfYWRkABgGZnJfc3ViABkGZnJfbmVnABoGZnJfbXVsACIKZnJfaW52ZXJzZQAjB2ZyX2NvcHkAAAdmcl96ZXJvAAEGZnJfb25lACEJZnJfaXNaZXJvAAIFZnJfZXEABAlnMV9pc1plcm8AJAdnMV9jb3B5ACYHZzFfemVybwAlCWcxX2RvdWJsZQAnBmcxX2FkZAAoBmcxX25lZwApBmcxX3N1YgAqEWcxX2Zyb21Nb250Z29tZXJ5ACsPZzFfdG9Nb250Z29tZXJ5ACwJZzFfYWZmaW5lAC0OZzFfdGltZXNTY2FsYXIALgtnMV9tdWx0aWV4cAA1DGcxX211bHRpZXhwMgA5B2ZmdF9mZnQAQghmZnRfaWZmdABDEWZmdF90b01vbnRnb21lcnlOAD8TZmZ0X2Zyb21Nb250Z29tZXJ5TgA+FGZmdF9jb3B5TkludGVybGVhdmVkAD0IZmZ0X211bE4ARAhwb2xfemVybwBFD3BvbF9jb25zdHJ1Y3RMQwBGCmYybV9pc1plcm8ARwhmMm1femVybwBIB2YybV9vbmUASQhmMm1fY29weQBKB2YybV9tdWwASwdmMm1fYWRkAEwHZjJtX3N1YgBNB2YybV9uZWcAThJmMm1fZnJvbU1vbnRnb21lcnkAUBBmMm1fdG9Nb250Z29tZXJ5AE8GZjJtX2VxAFELZjJtX2ludmVyc2UAUglnMl9pc1plcm8AUwdnMl9jb3B5AFUHZzJfemVybwBUCWcyX2RvdWJsZQBWBmcyX2FkZABXBmcyX25lZwBYBmcyX3N1YgBZEWcyX2Zyb21Nb250Z29tZXJ5AFoPZzJfdG9Nb250Z29tZXJ5AFsJZzJfYWZmaW5lAFwOZzJfdGltZXNTY2FsYXIAXQtnMl9tdWx0aWV4cABkDGcyX211bHRpZXhwMgBoDHRlc3RfZjFtX211bABpD3Rlc3RfZjFtX211bE9sZABqCsfEAWsqACABIAApAwA3AwAgASAAKQMINwMIIAEgACkDEDcDECABIAApAxg3AxgLHgAgAEIANwMAIABCADcDCCAAQgA3AxAgAEIANwMYCzMAIAApAxhQBEAgACkDEFAEQCAAKQMIUARAIAApAwBQDwVBAA8LBUEADwsFQQAPC0EADwseACAAQgE3AwAgAEIANwMIIABCADcDECAAQgA3AxgLRwAgACkDGCABKQMYUQRAIAApAxAgASkDEFEEQCAAKQMIIAEpAwhRBEAgACkDACABKQMAUQ8FQQAPCwVBAA8LBUEADwtBAA8LfQAgACkDGCABKQMYVARAQQAPBSAAKQMYIAEpAxhWBEBBAQ8FIAApAxAgASkDEFQEQEEADwUgACkDECABKQMQVgRAQQEPBSAAKQMIIAEpAwhUBEBBAA8FIAApAwggASkDCFYEQEEBDwUgACkDACABKQMAWg8LCwsLCwtBAA8L1AEBAX4gADUCACABNQIAfCEDIAIgAz4CACAANQIEIAE1AgR8IANCIIh8IQMgAiADPgIEIAA1AgggATUCCHwgA0IgiHwhAyACIAM+AgggADUCDCABNQIMfCADQiCIfCEDIAIgAz4CDCAANQIQIAE1AhB8IANCIIh8IQMgAiADPgIQIAA1AhQgATUCFHwgA0IgiHwhAyACIAM+AhQgADUCGCABNQIYfCADQiCIfCEDIAIgAz4CGCAANQIcIAE1Ahx8IANCIIh8IQMgAiADPgIcIANCIIinC4wCAQF+IAA1AgAgATUCAH0hAyACIANC/////w+DPgIAIAA1AgQgATUCBH0gA0Igh3whAyACIANC/////w+DPgIEIAA1AgggATUCCH0gA0Igh3whAyACIANC/////w+DPgIIIAA1AgwgATUCDH0gA0Igh3whAyACIANC/////w+DPgIMIAA1AhAgATUCEH0gA0Igh3whAyACIANC/////w+DPgIQIAA1AhQgATUCFH0gA0Igh3whAyACIANC/////w+DPgIUIAA1AhggATUCGH0gA0Igh3whAyACIANC/////w+DPgIYIAA1AhwgATUCHH0gA0Igh3whAyACIANC/////w+DPgIcIANCIIenC48QEgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfiADQv////8PgyAANQIAIgUgATUCACIGfnwhAyAEIANCIIh8IQQgAiADPgIAIARCIIghAyAEQv////8PgyAFIAE1AgQiCH58IQQgAyAEQiCIfCEDIARC/////w+DIAA1AgQiByAGfnwhBCADIARCIIh8IQMgAiAEPgIEIANCIIghBCADQv////8PgyAFIAE1AggiCn58IQMgBCADQiCIfCEEIANC/////w+DIAcgCH58IQMgBCADQiCIfCEEIANC/////w+DIAA1AggiCSAGfnwhAyAEIANCIIh8IQQgAiADPgIIIARCIIghAyAEQv////8PgyAFIAE1AgwiDH58IQQgAyAEQiCIfCEDIARC/////w+DIAcgCn58IQQgAyAEQiCIfCEDIARC/////w+DIAkgCH58IQQgAyAEQiCIfCEDIARC/////w+DIAA1AgwiCyAGfnwhBCADIARCIIh8IQMgAiAEPgIMIANCIIghBCADQv////8PgyAFIAE1AhAiDn58IQMgBCADQiCIfCEEIANC/////w+DIAcgDH58IQMgBCADQiCIfCEEIANC/////w+DIAkgCn58IQMgBCADQiCIfCEEIANC/////w+DIAsgCH58IQMgBCADQiCIfCEEIANC/////w+DIAA1AhAiDSAGfnwhAyAEIANCIIh8IQQgAiADPgIQIARCIIghAyAEQv////8PgyAFIAE1AhQiEH58IQQgAyAEQiCIfCEDIARC/////w+DIAcgDn58IQQgAyAEQiCIfCEDIARC/////w+DIAkgDH58IQQgAyAEQiCIfCEDIARC/////w+DIAsgCn58IQQgAyAEQiCIfCEDIARC/////w+DIA0gCH58IQQgAyAEQiCIfCEDIARC/////w+DIAA1AhQiDyAGfnwhBCADIARCIIh8IQMgAiAEPgIUIANCIIghBCADQv////8PgyAFIAE1AhgiEn58IQMgBCADQiCIfCEEIANC/////w+DIAcgEH58IQMgBCADQiCIfCEEIANC/////w+DIAkgDn58IQMgBCADQiCIfCEEIANC/////w+DIAsgDH58IQMgBCADQiCIfCEEIANC/////w+DIA0gCn58IQMgBCADQiCIfCEEIANC/////w+DIA8gCH58IQMgBCADQiCIfCEEIANC/////w+DIAA1AhgiESAGfnwhAyAEIANCIIh8IQQgAiADPgIYIARCIIghAyAEQv////8PgyAFIAE1AhwiFH58IQQgAyAEQiCIfCEDIARC/////w+DIAcgEn58IQQgAyAEQiCIfCEDIARC/////w+DIAkgEH58IQQgAyAEQiCIfCEDIARC/////w+DIAsgDn58IQQgAyAEQiCIfCEDIARC/////w+DIA0gDH58IQQgAyAEQiCIfCEDIARC/////w+DIA8gCn58IQQgAyAEQiCIfCEDIARC/////w+DIBEgCH58IQQgAyAEQiCIfCEDIARC/////w+DIAA1AhwiEyAGfnwhBCADIARCIIh8IQMgAiAEPgIcIANCIIghBCADQv////8PgyAHIBR+fCEDIAQgA0IgiHwhBCADQv////8PgyAJIBJ+fCEDIAQgA0IgiHwhBCADQv////8PgyALIBB+fCEDIAQgA0IgiHwhBCADQv////8PgyANIA5+fCEDIAQgA0IgiHwhBCADQv////8PgyAPIAx+fCEDIAQgA0IgiHwhBCADQv////8PgyARIAp+fCEDIAQgA0IgiHwhBCADQv////8PgyATIAh+fCEDIAQgA0IgiHwhBCACIAM+AiAgBEIgiCEDIARC/////w+DIAkgFH58IQQgAyAEQiCIfCEDIARC/////w+DIAsgEn58IQQgAyAEQiCIfCEDIARC/////w+DIA0gEH58IQQgAyAEQiCIfCEDIARC/////w+DIA8gDn58IQQgAyAEQiCIfCEDIARC/////w+DIBEgDH58IQQgAyAEQiCIfCEDIARC/////w+DIBMgCn58IQQgAyAEQiCIfCEDIAIgBD4CJCADQiCIIQQgA0L/////D4MgCyAUfnwhAyAEIANCIIh8IQQgA0L/////D4MgDSASfnwhAyAEIANCIIh8IQQgA0L/////D4MgDyAQfnwhAyAEIANCIIh8IQQgA0L/////D4MgESAOfnwhAyAEIANCIIh8IQQgA0L/////D4MgEyAMfnwhAyAEIANCIIh8IQQgAiADPgIoIARCIIghAyAEQv////8PgyANIBR+fCEEIAMgBEIgiHwhAyAEQv////8PgyAPIBJ+fCEEIAMgBEIgiHwhAyAEQv////8PgyARIBB+fCEEIAMgBEIgiHwhAyAEQv////8PgyATIA5+fCEEIAMgBEIgiHwhAyACIAQ+AiwgA0IgiCEEIANC/////w+DIA8gFH58IQMgBCADQiCIfCEEIANC/////w+DIBEgEn58IQMgBCADQiCIfCEEIANC/////w+DIBMgEH58IQMgBCADQiCIfCEEIAIgAz4CMCAEQiCIIQMgBEL/////D4MgESAUfnwhBCADIARCIIh8IQMgBEL/////D4MgEyASfnwhBCADIARCIIh8IQMgAiAEPgI0IANCIIghBCADQv////8PgyATIBR+fCEDIAQgA0IgiHwhBCACIAM+AjggBEIgiCEDIAIgBD4CPAv0EAEBfkEoIAA1AgAgATUCAH43AwBBKCAANQIAIAE1AgR+NwMIQSggADUCACABNQIIfjcDEEEoIAA1AgAgATUCDH43AxhBKCAANQIAIAE1AhB+NwMgQSggADUCACABNQIUfjcDKEEoIAA1AgAgATUCGH43AzBBKCAANQIAIAE1Ahx+NwM4QSggADUCBCABNQIAfjcDQEEoIAA1AgQgATUCBH43A0hBKCAANQIEIAE1Agh+NwNQQSggADUCBCABNQIMfjcDWEEoIAA1AgQgATUCEH43A2BBKCAANQIEIAE1AhR+NwNoQSggADUCBCABNQIYfjcDcEEoIAA1AgQgATUCHH43A3hBKCAANQIIIAE1AgB+NwOAAUEoIAA1AgggATUCBH43A4gBQSggADUCCCABNQIIfjcDkAFBKCAANQIIIAE1Agx+NwOYAUEoIAA1AgggATUCEH43A6ABQSggADUCCCABNQIUfjcDqAFBKCAANQIIIAE1Ahh+NwOwAUEoIAA1AgggATUCHH43A7gBQSggADUCDCABNQIAfjcDwAFBKCAANQIMIAE1AgR+NwPIAUEoIAA1AgwgATUCCH43A9ABQSggADUCDCABNQIMfjcD2AFBKCAANQIMIAE1AhB+NwPgAUEoIAA1AgwgATUCFH43A+gBQSggADUCDCABNQIYfjcD8AFBKCAANQIMIAE1Ahx+NwP4AUEoIAA1AhAgATUCAH43A4ACQSggADUCECABNQIEfjcDiAJBKCAANQIQIAE1Agh+NwOQAkEoIAA1AhAgATUCDH43A5gCQSggADUCECABNQIQfjcDoAJBKCAANQIQIAE1AhR+NwOoAkEoIAA1AhAgATUCGH43A7ACQSggADUCECABNQIcfjcDuAJBKCAANQIUIAE1AgB+NwPAAkEoIAA1AhQgATUCBH43A8gCQSggADUCFCABNQIIfjcD0AJBKCAANQIUIAE1Agx+NwPYAkEoIAA1AhQgATUCEH43A+ACQSggADUCFCABNQIUfjcD6AJBKCAANQIUIAE1Ahh+NwPwAkEoIAA1AhQgATUCHH43A/gCQSggADUCGCABNQIAfjcDgANBKCAANQIYIAE1AgR+NwOIA0EoIAA1AhggATUCCH43A5ADQSggADUCGCABNQIMfjcDmANBKCAANQIYIAE1AhB+NwOgA0EoIAA1AhggATUCFH43A6gDQSggADUCGCABNQIYfjcDsANBKCAANQIYIAE1Ahx+NwO4A0EoIAA1AhwgATUCAH43A8ADQSggADUCHCABNQIEfjcDyANBKCAANQIcIAE1Agh+NwPQA0EoIAA1AhwgATUCDH43A9gDQSggADUCHCABNQIQfjcD4ANBKCAANQIcIAE1AhR+NwPoA0EoIAA1AhwgATUCGH43A/ADQSggADUC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6Ac1AhAgBH58IQMgACADPgIkIAA1AiggA0IgiHxB6Ac1AhQgBH58IQMgACADPgIoIAA1AiwgA0IgiHxB6Ac1AhggBH58IQMgACADPgIsIAA1AjAgA0IgiHxB6Ac1AhwgBH58IQMgACADPgIwQegIIANCIIg+AhRCACEDIAA1AhggAn5C/////w+DIQQgADUCGCADQiCIfEHoBzUCACAEfnwhAyAAIAM+AhggADUCHCADQiCIfEHoBzUCBCAEfnwhAyAAIAM+AhwgADUCICADQiCIfEHoBzUCCCAEfnwhAyAAIAM+AiAgADUCJCADQiCIfEHoBzUCDCAEfnwhAyAAIAM+AiQgADUCKCADQiCIfEHoBzUCECAEfnwhAyAAIAM+AiggADUCLCADQiCIfEHoBzUCFCAEfnwhAyAAIAM+AiwgADUCMCADQiCIfEHoBzUCGCAEfnwhAyAAIAM+AjAgADUCNCADQiCIfEHoBzUCHCAEfnwhAyAAIAM+AjRB6AggA0IgiD4CGEIAIQMgADUCHCACfkL/////D4MhBCAANQIcIANCIIh8QegHNQIAIAR+fCEDIAAgAz4CHCAANQIgIANCIIh8QegHNQIEIAR+fCEDIAAgAz4CICAANQIkIANCIIh8QegHNQIIIAR+fCEDIAAgAz4CJCAANQIoIANCIIh8QegHNQIMIAR+fCEDIAAgAz4CKCAANQIsIANCIIh8QegHNQIQIAR+fCEDIAAgAz4CLCAANQIwIANCIIh8QegHNQIUIAR+fCEDIAAgAz4CMCAANQI0IANCIIh8QegHNQIYIAR+fCEDIAAgAz4CNCAANQI4IANCIIh8QegHNQIcIAR+fCEDIAAgAz4COEHoCCADQiCIPgIcQegIIABBIGogARAOC74fIwF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX5CiceZpA4hBSADQv////8PgyAANQIAIgYgATUCACIHfnwhAyAEIANCIIh8IQQgA0L/////D4MgBX5C/////w+DIQggA0L/////D4NBADUC6AciCSAIfnwhAyAEIANCIIh8IQQgBEIgiCEDIARC/////w+DIAYgATUCBCILfnwhBCADIARCIIh8IQMgBEL/////D4MgADUCBCIKIAd+fCEEIAMgBEIgiHwhAyAEQv////8Pg0EANQLsByINIAh+fCEEIAMgBEIgiHwhAyAEQv////8PgyAFfkL/////D4MhDCAEQv////8PgyAJIAx+fCEEIAMgBEIgiHwhAyADQiCIIQQgA0L/////D4MgBiABNQIIIg9+fCEDIAQgA0IgiHwhBCADQv////8PgyAKIAt+fCEDIAQgA0IgiHwhBCADQv////8PgyAANQIIIg4gB358IQMgBCADQiCIfCEEIANC/////w+DIA0gDH58IQMgBCADQiCIfCEEIANC/////w+DQQA1AvAHIhEgCH58IQMgBCADQiCIfCEEIANC/////w+DIAV+Qv////8PgyEQIANC/////w+DIAkgEH58IQMgBCADQiCIfCEEIARCIIghAyAEQv////8PgyAGIAE1AgwiE358IQQgAyAEQiCIfCEDIARC/////w+DIAogD358IQQgAyAEQiCIfCEDIARC/////w+DIA4gC358IQQgAyAEQiCIfCEDIARC/////w+DIAA1AgwiEiAHfnwhBCADIARCIIh8IQMgBEL/////D4MgDSAQfnwhBCADIARCIIh8IQMgBEL/////D4MgESAMfnwhBCADIARCIIh8IQMgBEL/////D4NBADUC9AciFSAIfnwhBCADIARCIIh8IQMgBEL/////D4MgBX5C/////w+DIRQgBEL/////D4MgCSAUfnwhBCADIARCIIh8IQMgA0IgiCEEIANC/////w+DIAYgATUCECIXfnwhAyAEIANCIIh8IQQgA0L/////D4MgCiATfnwhAyAEIANCIIh8IQQgA0L/////D4MgDiAPfnwhAyAEIANCIIh8IQQgA0L/////D4MgEiALfnwhAyAEIANCIIh8IQQgA0L/////D4MgADUCECIWIAd+fCEDIAQgA0IgiHwhBCADQv////8PgyANIBR+fCEDIAQgA0IgiHwhBCADQv////8PgyARIBB+fCEDIAQgA0IgiHwhBCADQv////8PgyAVIAx+fCEDIAQgA0IgiHwhBCADQv////8Pg0EANQL4ByIZIAh+fCEDIAQgA0IgiHwhBCADQv////8PgyAFfkL/////D4MhGCADQv////8PgyAJIBh+fCEDIAQgA0IgiHwhBCAEQiCIIQMgBEL/////D4MgBiABNQIUIht+fCEEIAMgBEIgiHwhAyAEQv////8PgyAKIBd+fCEEIAMgBEIgiHwhAyAEQv////8PgyAOIBN+fCEEIAMgBEIgiHwhAyAEQv////8PgyASIA9+fCEEIAMgBEIgiHwhAyAEQv////8PgyAWIAt+fCEEIAMgBEIgiHwhAyAEQv////8PgyAANQIUIhogB358IQQgAyAEQiCIfCEDIARC/////w+DIA0gGH58IQQgAyAEQiCIfCEDIARC/////w+DIBEgFH58IQQgAyAEQiCIfCEDIARC/////w+DIBUgEH58IQQgAyAEQiCIfCEDIARC/////w+DIBkgDH58IQQgAyAEQiCIfCEDIARC/////w+DQQA1AvwHIh0gCH58IQQgAyAEQiCIfCEDIARC/////w+DIAV+Qv////8PgyEcIARC/////w+DIAkgHH58IQQgAyAEQiCIfCEDIANCIIghBCADQv////8PgyAGIAE1AhgiH358IQMgBCADQiCIfCEEIANC/////w+DIAogG358IQMgBCADQiCIfCEEIANC/////w+DIA4gF358IQMgBCADQiCIfCEEIANC/////w+DIBIgE358IQMgBCADQiCIfCEEIANC/////w+DIBYgD358IQMgBCADQiCIfCEEIANC/////w+DIBogC358IQMgBCADQiCIfCEEIANC/////w+DIAA1AhgiHiAHfnwhAyAEIANCIIh8IQQgA0L/////D4MgDSAcfnwhAyAEIANCIIh8IQQgA0L/////D4MgESAYfnwhAyAEIANCIIh8IQQgA0L/////D4MgFSAUfnwhAyAEIANCIIh8IQQgA0L/////D4MgGSAQfnwhAyAEIANCIIh8IQQgA0L/////D4MgHSAMfnwhAyAEIANCIIh8IQQgA0L/////D4NBADUCgAgiISAIfnwhAyAEIANCIIh8IQQgA0L/////D4MgBX5C/////w+DISAgA0L/////D4MgCSAgfnwhAyAEIANCIIh8IQQgBEIgiCEDIARC/////w+DIAYgATUCHCIjfnwhBCADIARCIIh8IQMgBEL/////D4MgCiAffnwhBCADIARCIIh8IQMgBEL/////D4MgDiAbfnwhBCADIARCIIh8IQMgBEL/////D4MgEiAXfnwhBCADIARCIIh8IQMgBEL/////D4MgFiATfnwhBCADIARCIIh8IQMgBEL/////D4MgGiAPfnwhBCADIARCIIh8IQMgBEL/////D4MgHiALfnwhBCADIARCIIh8IQMgBEL/////D4MgADUCHCIiIAd+fCEEIAMgBEIgiHwhAyAEQv////8PgyANICB+fCEEIAMgBEIgiHwhAyAEQv////8PgyARIBx+fCEEIAMgBEIgiHwhAyAEQv////8PgyAVIBh+fCEEIAMgBEIgiHwhAyAEQv////8PgyAZIBR+fCEEIAMgBEIgiHwhAyAEQv////8PgyAdIBB+fCEEIAMgBEIgiHwhAyAEQv////8PgyAhIAx+fCEEIAMgBEIgiHwhAyAEQv////8Pg0EANQKECCIlIAh+fCEEIAMgBEIgiHwhAyAEQv////8PgyAFfkL/////D4MhJCAEQv////8PgyAJICR+fCEEIAMgBEIgiHwhAyADQiCIIQQgA0L/////D4MgCiAjfnwhAyAEIANCIIh8IQQgA0L/////D4MgDiAffnwhAyAEIANCIIh8IQQgA0L/////D4MgEiAbfnwhAyAEIANCIIh8IQQgA0L/////D4MgFiAXfnwhAyAEIANCIIh8IQQgA0L/////D4MgGiATfnwhAyAEIANCIIh8IQQgA0L/////D4MgHiAPfnwhAyAEIANCIIh8IQQgA0L/////D4MgIiALfnwhAyAEIANCIIh8IQQgA0L/////D4MgDSAkfnwhAyAEIANCIIh8IQQgA0L/////D4MgESAgfnwhAyAEIANCIIh8IQQgA0L/////D4MgFSAcfnwhAyAEIANCIIh8IQQgA0L/////D4MgGSAYfnwhAyAEIANCIIh8IQQgA0L/////D4MgHSAUfnwhAyAEIANCIIh8IQQgA0L/////D4MgISAQfnwhAyAEIANCIIh8IQQgA0L/////D4MgJSAMfnwhAyAEIANCIIh8IQQgAiADPgIAIARCIIghAyAEQv////8PgyAOICN+fCEEIAMgBEIgiHwhAyAEQv////8PgyASIB9+fCEEIAMgBEIgiHwhAyAEQv////8PgyAWIBt+fCEEIAMgBEIgiHwhAyAEQv////8PgyAaIBd+fCEEIAMgBEIgiHwhAyAEQv////8PgyAeIBN+fCEEIAMgBEIgiHwhAyAEQv////8PgyAiIA9+fCEEIAMgBEIgiHwhAyAEQv////8PgyARICR+fCEEIAMgBEIgiHwhAyAEQv////8PgyAVICB+fCEEIAMgBEIgiHwhAyAEQv////8PgyAZIBx+fCEEIAMgBEIgiHwhAyAEQv////8PgyAdIBh+fCEEIAMgBEIgiHwhAyAEQv////8PgyAhIBR+fCEEIAMgBEIgiHwhAyAEQv////8PgyAlIBB+fCEEIAMgBEIgiHwhAyACIAQ+AgQgA0IgiCEEIANC/////w+DIBIgI358IQMgBCADQiCIfCEEIANC/////w+DIBYgH358IQMgBCADQiCIfCEEIANC/////w+DIBogG358IQMgBCADQiCIfCEEIANC/////w+DIB4gF358IQMgBCADQiCIfCEEIANC/////w+DICIgE358IQMgBCADQiCIfCEEIANC/////w+DIBUgJH58IQMgBCADQiCIfCEEIANC/////w+DIBkgIH58IQMgBCADQiCIfCEEIANC/////w+DIB0gHH58IQMgBCADQiCIfCEEIANC/////w+DICEgGH58IQMgBCADQiCIfCEEIANC/////w+DICUgFH58IQMgBCADQiCIfCEEIAIgAz4CCCAEQiCIIQMgBEL/////D4MgFiAjfnwhBCADIARCIIh8IQMgBEL/////D4MgGiAffnwhBCADIARCIIh8IQMgBEL/////D4MgHiAbfnwhBCADIARCIIh8IQMgBEL/////D4MgIiAXfnwhBCADIARCIIh8IQMgBEL/////D4MgGSAkfnwhBCADIARCIIh8IQMgBEL/////D4MgHSAgfnwhBCADIARCIIh8IQMgBEL/////D4MgISAcfnwhBCADIARCIIh8IQMgBEL/////D4MgJSAYfnwhBCADIARCIIh8IQMgAiAEPgIMIANCIIghBCADQv////8PgyAaICN+fCEDIAQgA0IgiHwhBCADQv////8PgyAeIB9+fCEDIAQgA0IgiHwhBCADQv////8PgyAiIBt+fCEDIAQgA0IgiHwhBCADQv////8PgyAdICR+fCEDIAQgA0IgiHwhBCADQv////8PgyAhICB+fCEDIAQgA0IgiHwhBCADQv////8PgyAlIBx+fCEDIAQgA0IgiHwhBCACIAM+AhAgBEIgiCEDIARC/////w+DIB4gI358IQQgAyAEQiCIfCEDIARC/////w+DICIgH358IQQgAyAEQiCIfCEDIARC/////w+DICEgJH58IQQgAyAEQiCIfCEDIARC/////w+DICUgIH58IQQgAyAEQiCIfCEDIAIgBD4CFCADQiCIIQQgA0L/////D4MgIiAjfnwhAyAEIANCIIh8IQQgA0L/////D4MgJSAkfnwhAyAEIANCIIh8IQQgAiADPgIYIARCIIghAyACIAQ+AhwgA6cEQCACQegHIAIQBxoFIAJB6AcQBQRAIAJB6AcgAhAHGgsLCxIAIAAgAUHoDBAJQegMIAIQEQsLACAAQYgIIAEQEgsVACAAQagNEABByA0QAUGoDSABEBELFwAgACABEBUgAUHoByABEA0gASABEBQLCQBBqAggABAACywAIAAgASACEAYEQCACQegNIAIQBxoFIAJB6A0QBQRAIAJB6A0gAhAHGgsLCxcAIAAgASACEAcEQCACQegNIAIQBhoLCxQAIAAQAkUEQEHoDSAAIAEQBxoLC5wRAwF+AX4BfkL/////DiECQgAhAyAANQIAIAJ+Qv////8PgyEEIAA1AgAgA0IgiHxB6A01AgAgBH58IQMgACADPgIAIAA1AgQgA0IgiHxB6A01AgQgBH58IQMgACADPgIEIAA1AgggA0IgiHxB6A01AgggBH58IQMgACADPgIIIAA1AgwgA0IgiHxB6A01AgwgBH58IQMgACADPgIMIAA1AhAgA0IgiHxB6A01AhAgBH58IQMgACADPgIQIAA1AhQgA0IgiHxB6A01AhQgBH58IQMgACADPgIUIAA1AhggA0IgiHxB6A01AhggBH58IQMgACADPgIYIAA1AhwgA0IgiHxB6A01AhwgBH58IQMgACADPgIcQegOIANCIIg+AgBCACEDIAA1AgQgAn5C/////w+DIQQgADUCBCADQiCIfEHoDTUCACAEfnwhAyAAIAM+AgQgADUCCCADQiCIfEHoDTUCBCAEfnwhAyAAIAM+AgggADUCDCADQiCIfEHoDTUCCCAEfnwhAyAAIAM+AgwgADUCECADQiCIfEHoDTUCDCAEfnwhAyAAIAM+AhAgADUCFCADQiCIfEHoDTUCECAEfnwhAyAAIAM+AhQgADUCGCADQiCIfEHoDTUCFCAEfnwhAyAAIAM+AhggADUCHCADQiCIfEHoDTUCGCAEfnwhAyAAIAM+AhwgADUCICADQiCIfEHoDTUCHCAEfnwhAyAAIAM+AiBB6A4gA0IgiD4CBEIAIQMgADUCCCACfkL/////D4MhBCAANQIIIANCIIh8QegNNQIAIAR+fCEDIAAgAz4CCCAANQIMIANCIIh8QegNNQIEIAR+fCEDIAAgAz4CDCAANQIQIANCIIh8QegNNQIIIAR+fCEDIAAgAz4CECAANQIUIANCIIh8QegNNQIMIAR+fCEDIAAgAz4CFCAANQIYIANCIIh8QegNNQIQIAR+fCEDIAAgAz4CGCAANQIcIANCIIh8QegNNQIUIAR+fCEDIAAgAz4CHCAANQIgIANCIIh8QegNNQIYIAR+fCEDIAAgAz4CICAANQIkIANCIIh8QegNNQIcIAR+fCEDIAAgAz4CJEHoDiADQiCIPgIIQgAhAyAANQIMIAJ+Qv////8PgyEEIAA1AgwgA0IgiHxB6A01AgAgBH58IQMgACADPgIMIAA1AhAgA0IgiHxB6A01AgQgBH58IQMgACADPgIQIAA1AhQgA0IgiHxB6A01AgggBH58IQMgACADPgIUIAA1AhggA0IgiHxB6A01AgwgBH58IQMgACADPgIYIAA1AhwgA0IgiHxB6A01AhAgBH58IQMgACADPgIcIAA1AiAgA0IgiHxB6A01AhQgBH58IQMgACADPgIgIAA1AiQgA0IgiHxB6A01AhggBH58IQMgACADPgIkIAA1AiggA0IgiHxB6A01AhwgBH58IQMgACADPgIoQegOIANCIIg+AgxCACEDIAA1AhAgAn5C/////w+DIQQgADUCECADQiCIfEHoDTUCACAEfnwhAyAAIAM+AhAgADUCFCADQiCIfEHoDTUCBCAEfnwhAyAAIAM+AhQgADUCGCADQiCIfEHoDTUCCCAEfnwhAyAAIAM+AhggADUCHCADQiCIfEHoDTUCDCAEfnwhAyAAIAM+AhwgADUCICADQiCIfEHoDTUCECAEfnwhAyAAIAM+AiAgADUCJCADQiCIfEHoDTUCFCAEfnwhAyAAIAM+AiQgADUCKCADQiCIfEHoDTUCGCAEfnwhAyAAIAM+AiggADUCLCADQiCIfEHoDTUCHCAEfnwhAyAAIAM+AixB6A4gA0IgiD4CEEIAIQMgADUCFCACfkL/////D4MhBCAANQIUIANCIIh8QegNNQIAIAR+fCEDIAAgAz4CFCAANQIYIANCIIh8QegNNQIEIAR+fCEDIAAgAz4CGCAANQIcIANCIIh8QegNNQIIIAR+fCEDIAAgAz4CHCAANQIgIANCIIh8QegNNQIMIAR+fCEDIAAgAz4CICAANQIkIANCIIh8QegNNQIQIAR+fCEDIAAgAz4CJCAANQIoIANCIIh8QegNNQIUIAR+fCEDIAAgAz4CKCAANQIsIANCIIh8QegNNQIYIAR+fCEDIAAgAz4CLCAANQIwIANCIIh8QegNNQIcIAR+fCEDIAAgAz4CMEHoDiADQiCIPgIUQgAhAyAANQIYIAJ+Qv////8PgyEEIAA1AhggA0IgiHxB6A01AgAgBH58IQMgACADPgIYIAA1AhwgA0IgiHxB6A01AgQgBH58IQMgACADPgIcIAA1AiAgA0IgiHxB6A01AgggBH58IQMgACADPgIgIAA1AiQgA0IgiHxB6A01AgwgBH58IQMgACADPgIkIAA1AiggA0IgiHxB6A01AhAgBH58IQMgACADPgIoIAA1AiwgA0IgiHxB6A01AhQgBH58IQMgACADPgIsIAA1AjAgA0IgiHxB6A01AhggBH58IQMgACADPgIwIAA1AjQgA0IgiHxB6A01AhwgBH58IQMgACADPgI0QegOIANCIIg+AhhCACEDIAA1AhwgAn5C/////w+DIQQgADUCHCADQiCIfEHoDTUCACAEfnwhAyAAIAM+AhwgADUCICADQiCIfEHoDTUCBCAEfnwhAyAAIAM+AiAgADUCJCADQiCIfEHoDTUCCCAEfnwhAyAAIAM+AiQgADUCKCADQiCIfEHoDTUCDCAEfnwhAyAAIAM+AiggADUCLCADQiCIfEHoDTUCECAEfnwhAyAAIAM+AiwgADUCMCADQiCIfEHoDTUCFCAEfnwhAyAAIAM+AjAgADUCNCADQiCIfEHoDTUCGCAEfnwhAyAAIAM+AjQgADUCOCADQiCIfEHoDTUCHCAEfnwhAyAAIAM+AjhB6A4gA0IgiD4CHEHoDiAAQSBqIAEQGAu+HyMBfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+AX4BfgF+Qv////8OIQUgA0L/////D4MgADUCACIGIAE1AgAiB358IQMgBCADQiCIfCEEIANC/////w+DIAV+Qv////8PgyEIIANC/////w+DQQA1AugNIgkgCH58IQMgBCADQiCIfCEEIARCIIghAyAEQv////8PgyAGIAE1AgQiC358IQQgAyAEQiCIfCEDIARC/////w+DIAA1AgQiCiAHfnwhBCADIARCIIh8IQMgBEL/////D4NBADUC7A0iDSAIfnwhBCADIARCIIh8IQMgBEL/////D4MgBX5C/////w+DIQwgBEL/////D4MgCSAMfnwhBCADIARCIIh8IQMgA0IgiCEEIANC/////w+DIAYgATUCCCIPfnwhAyAEIANCIIh8IQQgA0L/////D4MgCiALfnwhAyAEIANCIIh8IQQgA0L/////D4MgADUCCCIOIAd+fCEDIAQgA0IgiHwhBCADQv////8PgyANIAx+fCEDIAQgA0IgiHwhBCADQv////8Pg0EANQLwDSIRIAh+fCEDIAQgA0IgiHwhBCADQv////8PgyAFfkL/////D4MhECADQv////8PgyAJIBB+fCEDIAQgA0IgiHwhBCAEQiCIIQMgBEL/////D4MgBiABNQIMIhN+fCEEIAMgBEIgiHwhAyAEQv////8PgyAKIA9+fCEEIAMgBEIgiHwhAyAEQv////8PgyAOIAt+fCEEIAMgBEIgiHwhAyAEQv////8PgyAANQIMIhIgB358IQQgAyAEQiCIfCEDIARC/////w+DIA0gEH58IQQgAyAEQiCIfCEDIARC/////w+DIBEgDH58IQQgAyAEQiCIfCEDIARC/////w+DQQA1AvQNIhUgCH58IQQgAyAEQiCIfCEDIARC/////w+DIAV+Qv////8PgyEUIARC/////w+DIAkgFH58IQQgAyAEQiCIfCEDIANCIIghBCADQv////8PgyAGIAE1AhAiF358IQMgBCADQiCIfCEEIANC/////w+DIAogE358IQMgBCADQiCIfCEEIANC/////w+DIA4gD358IQMgBCADQiCIfCEEIANC/////w+DIBIgC358IQMgBCADQiCIfCEEIANC/////w+DIAA1AhAiFiAHfnwhAyAEIANCIIh8IQQgA0L/////D4MgDSAUfnwhAyAEIANCIIh8IQQgA0L/////D4MgESAQfnwhAyAEIANCIIh8IQQgA0L/////D4MgFSAMfnwhAyAEIANCIIh8IQQgA0L/////D4NBADUC+A0iGSAIfnwhAyAEIANCIIh8IQQgA0L/////D4MgBX5C/////w+DIRggA0L/////D4MgCSAYfnwhAyAEIANCIIh8IQQgBEIgiCEDIARC/////w+DIAYgATUCFCIbfnwhBCADIARCIIh8IQMgBEL/////D4MgCiAXfnwhBCADIARCIIh8IQMgBEL/////D4MgDiATfnwhBCADIARCIIh8IQMgBEL/////D4MgEiAPfnwhBCADIARCIIh8IQMgBEL/////D4MgFiALfnwhBCADIARCIIh8IQMgBEL/////D4MgADUCFCIaIAd+fCEEIAMgBEIgiHwhAyAEQv////8PgyANIBh+fCEEIAMgBEIgiHwhAyAEQv////8PgyARIBR+fCEEIAMgBEIgiHwhAyAEQv////8PgyAVIBB+fCEEIAMgBEIgiHwhAyAEQv////8PgyAZIAx+fCEEIAMgBEIgiHwhAyAEQv////8Pg0EANQL8DSIdIAh+fCEEIAMgBEIgiHwhAyAEQv////8PgyAFfkL/////D4MhHCAEQv////8PgyAJIBx+fCEEIAMgBEIgiHwhAyADQiCIIQQgA0L/////D4MgBiABNQIYIh9+fCEDIAQgA0IgiHwhBCADQv////8PgyAKIBt+fCEDIAQgA0IgiHwhBCADQv////8PgyAOIBd+fCEDIAQgA0IgiHwhBCADQv////8PgyASIBN+fCEDIAQgA0IgiHwhBCADQv////8PgyAWIA9+fCEDIAQgA0IgiHwhBCADQv////8PgyAaIAt+fCEDIAQgA0IgiHwhBCADQv////8PgyAANQIYIh4gB358IQMgBCADQiCIfCEEIANC/////w+DIA0gHH58IQMgBCADQiCIfCEEIANC/////w+DIBEgGH58IQMgBCADQiCIfCEEIANC/////w+DIBUgFH58IQMgBCADQiCIfCEEIANC/////w+DIBkgEH58IQMgBCADQiCIfCEEIANC/////w+DIB0gDH58IQMgBCADQiCIfCEEIANC/////w+DQQA1AoAOIiEgCH58IQMgBCADQiCIfCEEIANC/////w+DIAV+Qv////8PgyEgIANC/////w+DIAkgIH58IQMgBCADQiCIfCEEIARCIIghAyAEQv////8PgyAGIAE1AhwiI358IQQgAyAEQiCIfCEDIARC/////w+DIAogH358IQQgAyAEQiCIfCEDIARC/////w+DIA4gG358IQQgAyAEQiCIfCEDIARC/////w+DIBIgF358IQQgAyAEQiCIfCEDIARC/////w+DIBYgE358IQQgAyAEQiCIfCEDIARC/////w+DIBogD358IQQgAyAEQiCIfCEDIARC/////w+DIB4gC358IQQgAyAEQiCIfCEDIARC/////w+DIAA1AhwiIiAHfnwhBCADIARCIIh8IQMgBEL/////D4MgDSAgfnwhBCADIARCIIh8IQMgBEL/////D4MgESAcfnwhBCADIARCIIh8IQMgBEL/////D4MgFSAYfnwhBCADIARCIIh8IQMgBEL/////D4MgGSAUfnwhBCADIARCIIh8IQMgBEL/////D4MgHSAQfnwhBCADIARCIIh8IQMgBEL/////D4MgISAMfnwhBCADIARCIIh8IQMgBEL/////D4NBADUChA4iJSAIfnwhBCADIARCIIh8IQMgBEL/////D4MgBX5C/////w+DISQgBEL/////D4MgCSAkfnwhBCADIARCIIh8IQMgA0IgiCEEIANC/////w+DIAogI358IQMgBCADQiCIfCEEIANC/////w+DIA4gH358IQMgBCADQiCIfCEEIANC/////w+DIBIgG358IQMgBCADQiCIfCEEIANC/////w+DIBYgF358IQMgBCADQiCIfCEEIANC/////w+DIBogE358IQMgBCADQiCIfCEEIANC/////w+DIB4gD358IQMgBCADQiCIfCEEIANC/////w+DICIgC358IQMgBCADQiCIfCEEIANC/////w+DIA0gJH58IQMgBCADQiCIfCEEIANC/////w+DIBEgIH58IQMgBCADQiCIfCEEIANC/////w+DIBUgHH58IQMgBCADQiCIfCEEIANC/////w+DIBkgGH58IQMgBCADQiCIfCEEIANC/////w+DIB0gFH58IQMgBCADQiCIfCEEIANC/////w+DICEgEH58IQMgBCADQiCIfCEEIANC/////w+DICUgDH58IQMgBCADQiCIfCEEIAIgAz4CACAEQiCIIQMgBEL/////D4MgDiAjfnwhBCADIARCIIh8IQMgBEL/////D4MgEiAffnwhBCADIARCIIh8IQMgBEL/////D4MgFiAbfnwhBCADIARCIIh8IQMgBEL/////D4MgGiAXfnwhBCADIARCIIh8IQMgBEL/////D4MgHiATfnwhBCADIARCIIh8IQMgBEL/////D4MgIiAPfnwhBCADIARCIIh8IQMgBEL/////D4MgESAkfnwhBCADIARCIIh8IQMgBEL/////D4MgFSAgfnwhBCADIARCIIh8IQMgBEL/////D4MgGSAcfnwhBCADIARCIIh8IQMgBEL/////D4MgHSAYfnwhBCADIARCIIh8IQMgBEL/////D4MgISAUfnwhBCADIARCIIh8IQMgBEL/////D4MgJSAQfnwhBCADIARCIIh8IQMgAiAEPgIEIANCIIghBCADQv////8PgyASICN+fCEDIAQgA0IgiHwhBCADQv////8PgyAWIB9+fCEDIAQgA0IgiHwhBCADQv////8PgyAaIBt+fCEDIAQgA0IgiHwhBCADQv////8PgyAeIBd+fCEDIAQgA0IgiHwhBCADQv////8PgyAiIBN+fCEDIAQgA0IgiHwhBCADQv////8PgyAVICR+fCEDIAQgA0IgiHwhBCADQv////8PgyAZICB+fCEDIAQgA0IgiHwhBCADQv////8PgyAdIBx+fCEDIAQgA0IgiHwhBCADQv////8PgyAhIBh+fCEDIAQgA0IgiHwhBCADQv////8PgyAlIBR+fCEDIAQgA0IgiHwhBCACIAM+AgggBEIgiCEDIARC/////w+DIBYgI358IQQgAyAEQiCIfCEDIARC/////w+DIBogH358IQQgAyAEQiCIfCEDIARC/////w+DIB4gG358IQQgAyAEQiCIfCEDIARC/////w+DICIgF358IQQgAyAEQiCIfCEDIARC/////w+DIBkgJH58IQQgAyAEQiCIfCEDIARC/////w+DIB0gIH58IQQgAyAEQiCIfCEDIARC/////w+DICEgHH58IQQgAyAEQiCIfCEDIARC/////w+DICUgGH58IQQgAyAEQiCIfCEDIAIgBD4CDCADQiCIIQQgA0L/////D4MgGiAjfnwhAyAEIANCIIh8IQQgA0L/////D4MgHiAffnwhAyAEIANCIIh8IQQgA0L/////D4MgIiAbfnwhAyAEIANCIIh8IQQgA0L/////D4MgHSAkfnwhAyAEIANCIIh8IQQgA0L/////D4MgISAgfnwhAyAEIANCIIh8IQQgA0L/////D4MgJSAcfnwhAyAEIANCIIh8IQQgAiADPgIQIARCIIghAyAEQv////8PgyAeICN+fCEEIAMgBEIgiHwhAyAEQv////8PgyAiIB9+fCEEIAMgBEIgiHwhAyAEQv////8PgyAhICR+fCEEIAMgBEIgiHwhAyAEQv////8PgyAlICB+fCEEIAMgBEIgiHwhAyACIAQ+AhQgA0IgiCEEIANC/////w+DICIgI358IQMgBCADQiCIfCEEIANC/////w+DICUgJH58IQMgBCADQiCIfCEEIAIgAz4CGCAEQiCIIQMgAiAEPgIcIAOnBEAgAkHoDSACEAcaBSACQegNEAUEQCACQegNIAIQBxoLCwsSACAAIAFB6BIQCUHoEiACEBsLCwAgAEGIDiABEBwLFQAgAEGoExAAQcgTEAFBqBMgARAbCxcAIAAgARAfIAFB6A0gARANIAEgARAeCwkAQagOIAAQAAsVACAAIAFB6BMQHEHoE0GIDiACEBwLCwAgAEHoDSABEA0LCgAgAEHAAGoQAgsVACAAEAEgAEEgahAXIABBwABqEAELIgAgACABEAAgAEEgaiABQSBqEAAgAEHAAGogAUHAAGoQAAuGAgAgABAkBEAgACABECYPCyAAIABBiBQQEiAAQSBqIABBIGpBqBQQEkGoFEGoFEHIFBASIABBqBRB6BQQDkHoFEHoFEHoFBASQegUQYgUQegUEA9B6BRByBRB6BQQD0HoFEHoFEHoFBAOQYgUQYgUQYgVEA5BiBVBiBRBiBUQDkGIFUGIFUGoFRASIABBIGogAEHAAGpByBUQEkHoFEHoFCABEA5BqBUgASABEA9ByBRByBRB6BUQDkHoFUHoFUHoFRAOQegVQegVQegVEA5B6BQgASABQSBqEA8gAUEgakGIFSABQSBqEBIgAUEgakHoFSABQSBqEA9ByBVByBUgAUHAAGoQDgusAwIBfwF/IABBwABqIQMgAUHAAGohBCAAECQEQCABIAIQJg8LIAEQJARAIAAgAhAmDwsgAyADQYgWEBIgBCAEQagWEBIgAEGoFkHIFhASIAFBiBZB6BYQEiADQYgWQYgXEBIgBEGoFkGoFxASIABBIGpBqBdByBcQEiAB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IQUgAyEGIAAgAkEgbGohBwJAA0AgBCAHRg0BIAQgBSAGEBwgBEEgaiEEIAVBIGohBSAGQSBqIQYMAAsLCy4CAX8BfyAAIQMgACABQSBsaiECAkADQCADIAJGDQEgAxABIANBIGohAwwACwsLjgEGAX8BfwF/AX8BfwF/QQAhBCAAIQYgASEHAkADQCAEIAJGDQEgBigCACEJIAZBBGohBkEAIQUCQANAIAUgCUYNASADIAYoAgBBIGxqIQggBkEEaiEGIAcgBkGotwMQHEGotwMgCCAIEBggBkEgaiEGIAVBAWohBQwACwsgB0EgaiEHIARBAWohBAwACwsLDgAgABACIABBIGoQAnELDQAgABABIABBIGoQAQsNACAAEBcgAEEgahABCxQAIAAgARAAIABBIGogAUEgahAAC3kAIAAgAUHotwMQEiAAQSBqIAFBIGpBiLgDEBIgACAAQSBqQai4AxAOIAEgAUEgakHIuAMQDkGouANByLgDQai4AxASQYi4A0HItwMgAhASQei3AyACIAIQDkHotwNBiLgDIAJBIGoQDkGouAMgAkEgaiACQSBqEA8LGwAgACABIAIQDiAAQSBqIAFBIGogAkEgahAOCxsAIAAgASACEA8gAEEgaiABQSBqIAJBIGoQDwsUACAAIAEQECAAQSBqIAFBIGoQEAsUACAAIAEQFCAAQSBqIAFBIGoQFAsUACAAIAEQFSAAQSBqIAFBIGoQFQsVACAAIAEQBCAAQSBqIAFBIGoQBHELaAAgACAAQei4AxASIABBIGogAEEgakGIuQMQEkGIuQNByLcDQai5AxASQei4A0GouQNBqLkDEA9BqLkDQci5AxAWIABByLkDIAEQEiAAQSBqQci5AyABQSBqEBIgAUEgaiABQSBqEBALCgAgAEGAAWoQRwsWACAAEEggAEHAAGoQSSAAQYABahBICyQAIAAgARBKIABBwABqIAFBwABqEEogAEGAAWogAUGAAWoQSgu8AgAgABBTBEAgACABEFUPCyAAIABB6LkDEEsgAEHAAGogAEHAAGpBqLoDEEtBqLoDQai6A0HougMQSyAAQai6A0GouwMQTEGouwNBqLsDQai7AxBLQai7A0HouQNBqLsDEE1BqLsDQei6A0GouwMQTUGouwNBqLsDQai7AxBMQei5A0HouQNB6LsDEExB6LsDQei5A0HouwMQTEHouwNB6LsDQai8AxBLIABBwABqIABBgAFqQei8AxBLQai7A0GouwMgARBMQai8AyABIAEQTUHougNB6LoDQai9AxBMQai9A0GovQNBqL0DEExBqL0DQai9A0GovQMQTEGouwMgASABQcAAahBNIAFBwABqQei7AyABQcAAahBLIAFBwABqQai9AyABQcAAahBNQei8A0HovAMgAUGAAWoQTAvvAwIBfwF/IABBgAFqIQMgAUGAAWohBCAAEFMEQCABIAIQVQ8LIAEQUwRAIAAgAhBVDwsgAyADQei9AxBLIAQgBEGovgMQSyAAQai+A0HovgMQSyABQei9A0GovwMQSyADQei9A0HovwMQSyAEQai+A0GowAMQSyAAQcAAakGowANB6MADEEsgAUHAAGpB6L8DQajBAxBLQei+A0GovwMQUQRAQejAA0GowQMQUQRAIAAgAhBWDwsLQai/A0HovgNB6MEDEE1BqMEDQejAA0GowgMQTUHowQNB6MEDQejCAxBMQejCA0HowgNB6MIDEEtB6MEDQejCA0GowwMQS0GowgNBqMIDQejDAxBMQei+A0HowgNB6MQDEEtB6MMDQejDA0GoxAMQS0HoxANB6MQDQajFAxBMQajEA0GowwMgAhBNIAJBqMUDIAIQTUHowANBqMMDQejFAxBLQejFA0HoxQNB6MUDEExB6MQDIAIgAkHAAGoQTSACQcAAakHowwMgAkHAAGoQSyACQcAAakHoxQMgAkHAAGoQTSADIAQgAkGAAWoQTCACQYABaiACQYABaiACQYABahBLIAJBgAFqQei9AyACQYABahBNIAJBgAFqQai+AyACQYABahBNIAJBgAFqQejBAyACQYABahBLCyQAIAAgARBKIABBwABqIAFBwABqEE4gAEGAAWogAUGAAWoQSgsQACABIAIQWCAAIAIgAhBXCyQAIAAgARBQIABBwABqIAFBwABqEFAgAEGAAWogAUGAAWoQUAskACAAIAEQTyAAQcAAaiABQcAAahBPIABBgAFqIAFBgAFqEE8LWgAgABBTBEAgARBUBSAAQYABakGoxgMQUkGoxgNBqMYDQejGAxBLQajGA0HoxgNBqMcDEEsgAEHoxgMgARBLIABBwABqQajHAyABQcAAahBLIAFBgAFqEEkLC7ACAgF/AX8gAEHo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", "base64");
    exports2.pq = 1e3;
    exports2.pr = 1768;
  }
});

// groth16.js
var require_groth16 = __commonJS({
  "groth16.js"(exports2, module2) {
    var bigInt3 = require_BigInteger();
    var groth16_wasm = require_groth16_wasm();
    var assert = require("assert");
    var inBrowser = typeof window !== "undefined";
    var NodeWorker;
    var NodeCrypto;
    if (!inBrowser) {
      NodeWorker = require("worker_threads").Worker;
      NodeCrypto = require("crypto");
    }
    var Deferred = class {
      constructor() {
        this.promise = new Promise((resolve, reject) => {
          this.reject = reject;
          this.resolve = resolve;
        });
      }
    };
    function thread(self) {
      let instance;
      let memory;
      let i32;
      async function init(data) {
        const code = new Uint8Array(data.code);
        const wasmModule = await WebAssembly.compile(code);
        memory = new WebAssembly.Memory({ initial: data.init });
        i32 = new Uint32Array(memory.buffer);
        instance = await WebAssembly.instantiate(wasmModule, {
          env: {
            "memory": memory
          }
        });
      }
      function alloc(length) {
        while (i32[0] & 3) i32[0]++;
        const res = i32[0];
        i32[0] += length;
        while (i32[0] > memory.buffer.byteLength) {
          memory.grow(100);
        }
        i32 = new Uint32Array(memory.buffer);
        return res;
      }
      function putBin(b) {
        const p = alloc(b.byteLength);
        const s32 = new Uint32Array(b);
        i32.set(s32, p / 4);
        return p;
      }
      function getBin(p, l) {
        return memory.buffer.slice(p, p + l);
      }
      self.onmessage = function(e) {
        let data;
        if (e.data) {
          data = e.data;
        } else {
          data = e;
        }
        if (data.command == "INIT") {
          init(data).then(function() {
            self.postMessage(data.result);
          });
        } else if (data.command == "G1_MULTIEXP") {
          const oldAlloc = i32[0];
          const pScalars = putBin(data.scalars);
          const pPoints = putBin(data.points);
          const pRes = alloc(96);
          instance.exports.g1_zero(pRes);
          instance.exports.g1_multiexp2(pScalars, pPoints, data.n, 7, pRes);
          data.result = getBin(pRes, 96);
          i32[0] = oldAlloc;
          self.postMessage(data.result, [data.result]);
        } else if (data.command == "G2_MULTIEXP") {
          const oldAlloc = i32[0];
          const pScalars = putBin(data.scalars);
          const pPoints = putBin(data.points);
          const pRes = alloc(192);
          instance.exports.g2_zero(pRes);
          instance.exports.g2_multiexp(pScalars, pPoints, data.n, 7, pRes);
          data.result = getBin(pRes, 192);
          i32[0] = oldAlloc;
          self.postMessage(data.result, [data.result]);
        } else if (data.command == "CALC_H") {
          const oldAlloc = i32[0];
          const pSignals = putBin(data.signals);
          const pPolsA = putBin(data.polsA);
          const pPolsB = putBin(data.polsB);
          const nSignals = data.nSignals;
          const domainSize = data.domainSize;
          const pSignalsM = alloc(nSignals * 32);
          const pPolA = alloc(domainSize * 32);
          const pPolB = alloc(domainSize * 32);
          const pPolA2 = alloc(domainSize * 32 * 2);
          const pPolB2 = alloc(domainSize * 32 * 2);
          instance.exports.fft_toMontgomeryN(pSignals, pSignalsM, nSignals);
          instance.exports.pol_zero(pPolA, domainSize);
          instance.exports.pol_zero(pPolB, domainSize);
          instance.exports.pol_constructLC(pPolsA, pSignalsM, nSignals, pPolA);
          instance.exports.pol_constructLC(pPolsB, pSignalsM, nSignals, pPolB);
          instance.exports.fft_copyNInterleaved(pPolA, pPolA2, domainSize);
          instance.exports.fft_copyNInterleaved(pPolB, pPolB2, domainSize);
          instance.exports.fft_ifft(pPolA, domainSize, 0);
          instance.exports.fft_ifft(pPolB, domainSize, 0);
          instance.exports.fft_fft(pPolA, domainSize, 1);
          instance.exports.fft_fft(pPolB, domainSize, 1);
          instance.exports.fft_copyNInterleaved(pPolA, pPolA2 + 32, domainSize);
          instance.exports.fft_copyNInterleaved(pPolB, pPolB2 + 32, domainSize);
          instance.exports.fft_mulN(pPolA2, pPolB2, domainSize * 2, pPolA2);
          instance.exports.fft_ifft(pPolA2, domainSize * 2, 0);
          instance.exports.fft_fromMontgomeryN(pPolA2 + domainSize * 32, pPolA2 + domainSize * 32, domainSize);
          data.result = getBin(pPolA2 + domainSize * 32, domainSize * 32);
          i32[0] = oldAlloc;
          self.postMessage(data.result, [data.result]);
        } else if (data.command == "TERMINATE") {
          process.exit();
        }
      };
    }
    async function build(params) {
      const defaultParams = { wasmInitialMemory: 5e3 };
      Object.assign(defaultParams, params);
      const groth16 = new Groth16();
      groth16.q = bigInt3("21888242871839275222246405745257275088696311157297823662689037894645226208583");
      groth16.r = bigInt3("21888242871839275222246405745257275088548364400416034343698204186575808495617");
      groth16.n64 = Math.floor((groth16.q.minus(1).bitLength() - 1) / 64) + 1;
      groth16.n32 = groth16.n64 * 2;
      groth16.n8 = groth16.n64 * 8;
      groth16.memory = new WebAssembly.Memory({ initial: defaultParams.wasmInitialMemory });
      groth16.i32 = new Uint32Array(groth16.memory.buffer);
      const wasmModule = await WebAssembly.compile(groth16_wasm.code);
      groth16.instance = await WebAssembly.instantiate(wasmModule, {
        env: {
          "memory": groth16.memory
        }
      });
      groth16.pq = groth16_wasm.pq;
      groth16.pr = groth16_wasm.pr;
      groth16.pr0 = groth16.alloc(192);
      groth16.pr1 = groth16.alloc(192);
      groth16.workers = [];
      groth16.pendingDeferreds = [];
      groth16.working = [];
      let concurrency;
      if (typeof navigator === "object" && navigator.hardwareConcurrency) {
        concurrency = navigator.hardwareConcurrency;
      } else {
        concurrency = 8;
      }
      function getOnMsg(i) {
        return function(e) {
          let data;
          if (e && e.data) {
            data = e.data;
          } else {
            data = e;
          }
          groth16.working[i] = false;
          groth16.pendingDeferreds[i].resolve(data);
          groth16.processWorks();
        };
      }
      for (let i = 0; i < concurrency; i++) {
        if (inBrowser) {
          const blob = new Blob(["(", thread.toString(), ")(self);"], { type: "text/javascript" });
          const url = URL.createObjectURL(blob);
          groth16.workers[i] = new Worker(url);
          groth16.workers[i].onmessage = getOnMsg(i);
        } else {
          groth16.workers[i] = new NodeWorker("(" + thread.toString() + ")(require('worker_threads').parentPort);", { eval: true });
          groth16.workers[i].on("message", getOnMsg(i));
        }
        groth16.working[i] = false;
      }
      const initPromises = [];
      for (let i = 0; i < groth16.workers.length; i++) {
        const copyCode = groth16_wasm.code.buffer.slice(0);
        initPromises.push(groth16.postAction(i, {
          command: "INIT",
          init: defaultParams.wasmInitialMemory,
          code: copyCode
        }, [copyCode]));
      }
      await Promise.all(initPromises);
      return groth16;
    }
    var Groth16 = class {
      constructor() {
        this.actionQueue = [];
      }
      postAction(workerId, e, transfers, _deferred) {
        assert(this.working[workerId] == false);
        this.working[workerId] = true;
        this.pendingDeferreds[workerId] = _deferred ? _deferred : new Deferred();
        this.workers[workerId].postMessage(e, transfers);
        return this.pendingDeferreds[workerId].promise;
      }
      processWorks() {
        for (let i = 0; i < this.workers.length && this.actionQueue.length > 0; i++) {
          if (this.working[i] == false) {
            const work = this.actionQueue.shift();
            this.postAction(i, work.data, work.transfers, work.deferred);
          }
        }
      }
      queueAction(actionData, transfers) {
        const d = new Deferred();
        this.actionQueue.push({
          data: actionData,
          transfers,
          deferred: d
        });
        this.processWorks();
        return d.promise;
      }
      alloc(length) {
        while (this.i32[0] & 3) this.i32[0]++;
        const res = this.i32[0];
        this.i32[0] += length;
        return res;
      }
      putBin(p, b) {
        const s32 = new Uint32Array(b);
        this.i32.set(s32, p / 4);
      }
      getBin(p, l) {
        return this.memory.buffer.slice(p, p + l);
      }
      bin2int(b) {
        const i32 = new Uint32Array(b);
        let acc = bigInt3(i32[7]);
        for (let i = 6; i >= 0; i--) {
          acc = acc.shiftLeft(32);
          acc = acc.add(i32[i]);
        }
        return acc.toString();
      }
      bin2g1(b) {
        return [
          this.bin2int(b.slice(0, 32)),
          this.bin2int(b.slice(32, 64)),
          this.bin2int(b.slice(64, 96))
        ];
      }
      bin2g2(b) {
        return [
          [
            this.bin2int(b.slice(0, 32)),
            this.bin2int(b.slice(32, 64))
          ],
          [
            this.bin2int(b.slice(64, 96)),
            this.bin2int(b.slice(96, 128))
          ],
          [
            this.bin2int(b.slice(128, 160)),
            this.bin2int(b.slice(160, 192))
          ]
        ];
      }
      async g1_multiexp(scalars, points) {
        const nPoints = scalars.byteLength / 32;
        const nPointsPerThread = Math.floor(nPoints / this.workers.length);
        const opPromises = [];
        for (let i = 0; i < this.workers.length; i++) {
          const th_nPoints = i < this.workers.length - 1 ? nPointsPerThread : nPoints - nPointsPerThread * (this.workers.length - 1);
          const scalars_th = scalars.slice(i * nPointsPerThread * 32, i * nPointsPerThread * 32 + th_nPoints * 32);
          const points_th = points.slice(i * nPointsPerThread * 64, i * nPointsPerThread * 64 + th_nPoints * 64);
          opPromises.push(
            this.queueAction({
              command: "G1_MULTIEXP",
              scalars: scalars_th,
              points: points_th,
              n: th_nPoints
            }, [scalars_th, points_th])
          );
        }
        const results = await Promise.all(opPromises);
        this.instance.exports.g1_zero(this.pr0);
        for (let i = 0; i < results.length; i++) {
          this.putBin(this.pr1, results[i]);
          this.instance.exports.g1_add(this.pr0, this.pr1, this.pr0);
        }
        return this.getBin(this.pr0, 96);
      }
      async g2_multiexp(scalars, points) {
        const nPoints = scalars.byteLength / 32;
        const nPointsPerThread = Math.floor(nPoints / this.workers.length);
        const opPromises = [];
        for (let i = 0; i < this.workers.length; i++) {
          const th_nPoints = i < this.workers.length - 1 ? nPointsPerThread : nPoints - nPointsPerThread * (this.workers.length - 1);
          const scalars_th = scalars.slice(i * nPointsPerThread * 32, i * nPointsPerThread * 32 + th_nPoints * 32);
          const points_th = points.slice(i * nPointsPerThread * 128, i * nPointsPerThread * 128 + th_nPoints * 128);
          opPromises.push(
            this.queueAction({
              command: "G2_MULTIEXP",
              scalars: scalars_th,
              points: points_th,
              n: th_nPoints
            }, [scalars_th, points_th])
          );
        }
        const results = await Promise.all(opPromises);
        this.instance.exports.g2_zero(this.pr0);
        for (let i = 0; i < results.length; i++) {
          this.putBin(this.pr1, results[i]);
          this.instance.exports.g2_add(this.pr0, this.pr1, this.pr0);
        }
        return this.getBin(this.pr0, 192);
      }
      g1_affine(p) {
        this.putBin(this.pr0, p);
        this.instance.exports.g1_affine(this.pr0, this.pr0);
        return this.getBin(this.pr0, 96);
      }
      g2_affine(p) {
        this.putBin(this.pr0, p);
        this.instance.exports.g2_affine(this.pr0, this.pr0);
        return this.getBin(this.pr0, 192);
      }
      g1_fromMontgomery(p) {
        this.putBin(this.pr0, p);
        this.instance.exports.g1_fromMontgomery(this.pr0, this.pr0);
        return this.getBin(this.pr0, 96);
      }
      g2_fromMontgomery(p) {
        this.putBin(this.pr0, p);
        this.instance.exports.g2_fromMontgomery(this.pr0, this.pr0);
        return this.getBin(this.pr0, 192);
      }
      loadPoint1(b) {
        const p = this.alloc(96);
        this.putBin(p, b);
        this.instance.exports.f1m_one(p + 64);
        return p;
      }
      loadPoint2(b) {
        const p = this.alloc(192);
        this.putBin(p, b);
        this.instance.exports.f2m_one(p + 128);
        return p;
      }
      terminate() {
        for (let i = 0; i < this.workers.length; i++) {
          this.workers[i].postMessage({ command: "TERMINATE" });
        }
      }
      async calcH(signals, polsA, polsB, nSignals, domainSize) {
        return this.queueAction({
          command: "CALC_H",
          signals,
          polsA,
          polsB,
          nSignals,
          domainSize
        }, [signals, polsA, polsB]);
      }
      async proof(signals, pkey) {
        const pkey32 = new Uint32Array(pkey);
        const nSignals = pkey32[0];
        const nPublic = pkey32[1];
        const domainSize = pkey32[2];
        const pPolsA = pkey32[3];
        const pPolsB = pkey32[4];
        const pPointsA = pkey32[5];
        const pPointsB1 = pkey32[6];
        const pPointsB2 = pkey32[7];
        const pPointsC = pkey32[8];
        const pHExps = pkey32[9];
        const polsA = pkey.slice(pPolsA, pPolsA + pPolsB);
        const polsB = pkey.slice(pPolsB, pPolsB + pPointsA);
        const pointsA = pkey.slice(pPointsA, pPointsA + nSignals * 64);
        const pointsB1 = pkey.slice(pPointsB1, pPointsB1 + nSignals * 64);
        const pointsB2 = pkey.slice(pPointsB2, pPointsB2 + nSignals * 128);
        const pointsC = pkey.slice(pPointsC, pPointsC + (nSignals - nPublic - 1) * 64);
        const pointsHExps = pkey.slice(pHExps, pHExps + domainSize * 64);
        const alfa1 = pkey.slice(10 * 4, 10 * 4 + 64);
        const beta1 = pkey.slice(10 * 4 + 64, 10 * 4 + 128);
        const delta1 = pkey.slice(10 * 4 + 128, 10 * 4 + 192);
        const beta2 = pkey.slice(10 * 4 + 192, 10 * 4 + 320);
        const delta2 = pkey.slice(10 * 4 + 320, 10 * 4 + 448);
        const pH = this.calcH(signals.slice(0), polsA, polsB, nSignals, domainSize).then((h) => {
          return this.g1_multiexp(h, pointsHExps);
        });
        const pA = this.g1_multiexp(signals.slice(0), pointsA);
        const pB1 = this.g1_multiexp(signals.slice(0), pointsB1);
        const pB2 = this.g2_multiexp(signals.slice(0), pointsB2);
        const pC = this.g1_multiexp(signals.slice((nPublic + 1) * 32), pointsC);
        const res = await Promise.all([pA, pB1, pB2, pC, pH]);
        const pi_a = this.alloc(96);
        const pi_b = this.alloc(192);
        const pi_c = this.alloc(96);
        const pib1 = this.alloc(96);
        this.putBin(pi_a, res[0]);
        this.putBin(pib1, res[1]);
        this.putBin(pi_b, res[2]);
        this.putBin(pi_c, res[3]);
        const pAlfa1 = this.loadPoint1(alfa1);
        const pBeta1 = this.loadPoint1(beta1);
        const pDelta1 = this.loadPoint1(delta1);
        const pBeta2 = this.loadPoint2(beta2);
        const pDelta2 = this.loadPoint2(delta2);
        let rnd = new Uint32Array(8);
        const aux1 = this.alloc(96);
        const aux2 = this.alloc(192);
        const pr = this.alloc(32);
        const ps = this.alloc(32);
        if (inBrowser) {
          window.crypto.getRandomValues(rnd);
          this.putBin(pr, rnd);
          window.crypto.getRandomValues(rnd);
          this.putBin(ps, rnd);
        } else {
          const br = NodeCrypto.randomBytes(32);
          this.putBin(pr, br);
          const bs = NodeCrypto.randomBytes(32);
          this.putBin(ps, bs);
        }
        this.instance.exports.g1_add(pAlfa1, pi_a, pi_a);
        this.instance.exports.g1_timesScalar(pDelta1, pr, 32, aux1);
        this.instance.exports.g1_add(aux1, pi_a, pi_a);
        this.instance.exports.g2_add(pBeta2, pi_b, pi_b);
        this.instance.exports.g2_timesScalar(pDelta2, ps, 32, aux2);
        this.instance.exports.g2_add(aux2, pi_b, pi_b);
        this.instance.exports.g1_add(pBeta1, pib1, pib1);
        this.instance.exports.g1_timesScalar(pDelta1, ps, 32, aux1);
        this.instance.exports.g1_add(aux1, pib1, pib1);
        this.putBin(aux1, res[4]);
        this.instance.exports.g1_add(aux1, pi_c, pi_c);
        this.instance.exports.g1_timesScalar(pi_a, ps, 32, aux1);
        this.instance.exports.g1_add(aux1, pi_c, pi_c);
        this.instance.exports.g1_timesScalar(pib1, pr, 32, aux1);
        this.instance.exports.g1_add(aux1, pi_c, pi_c);
        const prs = this.alloc(64);
        this.instance.exports.int_mul(pr, ps, prs);
        this.instance.exports.g1_timesScalar(pDelta1, prs, 64, aux1);
        this.instance.exports.g1_neg(aux1, aux1);
        this.instance.exports.g1_add(aux1, pi_c, pi_c);
        this.instance.exports.g1_affine(pi_a, pi_a);
        this.instance.exports.g2_affine(pi_b, pi_b);
        this.instance.exports.g1_affine(pi_c, pi_c);
        this.instance.exports.g1_fromMontgomery(pi_a, pi_a);
        this.instance.exports.g2_fromMontgomery(pi_b, pi_b);
        this.instance.exports.g1_fromMontgomery(pi_c, pi_c);
        return {
          pi_a: this.bin2g1(this.getBin(pi_a, 96)),
          pi_b: this.bin2g2(this.getBin(pi_b, 192)),
          pi_c: this.bin2g1(this.getBin(pi_c, 96))
        };
      }
    };
    module2.exports = build;
  }
});

// ../../snarkjs/src/bigint.js
var require_bigint = __commonJS({
  "../../snarkjs/src/bigint.js"(exports2, module2) {
    var bigInt3 = require_BigInteger();
    var wBigInt;
    if (typeof BigInt != "undefined") {
      wBigInt = BigInt;
      wBigInt.one = wBigInt(1);
      wBigInt.zero = wBigInt(0);
      wBigInt.genAffine = (q) => {
        const nq = -q;
        return (a) => {
          let aux = a;
          if (aux < 0) {
            if (aux <= nq) {
              aux = aux % q;
            }
            if (aux < wBigInt.zero) {
              aux = aux + q;
            }
          } else {
            if (aux >= q) {
              aux = aux % q;
            }
          }
          return aux.valueOf();
        };
      };
      wBigInt.genInverse = (q) => {
        return (a) => {
          let t2 = wBigInt.zero;
          let r = q;
          let newt = wBigInt.one;
          let newr = wBigInt.affine(a, q);
          while (newr != wBigInt.zero) {
            let q2 = r / newr;
            [t2, newt] = [newt, t2 - q2 * newt];
            [r, newr] = [newr, r - q2 * newr];
          }
          if (t2 < wBigInt.zero) t2 += q;
          return t2;
        };
      };
      wBigInt.genAdd = (q) => {
        if (q) {
          return (a, b) => (a + b) % q;
        } else {
          return (a, b) => a + b;
        }
      };
      wBigInt.genSub = (q) => {
        if (q) {
          return (a, b) => (a - b) % q;
        } else {
          return (a, b) => a - b;
        }
      };
      wBigInt.genNeg = (q) => {
        if (q) {
          return (a) => -a % q;
        } else {
          return (a) => -a;
        }
      };
      wBigInt.genMul = (q) => {
        if (q) {
          return (a, b) => a * b % q;
        } else {
          return (a, b) => a * b;
        }
      };
      wBigInt.genShr = () => {
        return (a, b) => a >> wBigInt(b);
      };
      wBigInt.genShl = (q) => {
        if (q) {
          return (a, b) => (a << wBigInt(b)) % q;
        } else {
          return (a, b) => a << wBigInt(b);
        }
      };
      wBigInt.genEquals = (q) => {
        if (q) {
          return (a, b) => a.affine(q) == b.affine(q);
        } else {
          return (a, b) => a == b;
        }
      };
      wBigInt.genSquare = (q) => {
        if (q) {
          return (a) => a * a % q;
        } else {
          return (a) => a * a;
        }
      };
      wBigInt.genDouble = (q) => {
        if (q) {
          return (a) => (a + a) % q;
        } else {
          return (a) => a + a;
        }
      };
      wBigInt.genIsZero = (q) => {
        if (q) {
          return (a) => a.affine(q) == wBigInt.zero;
        } else {
          return (a) => a == wBigInt.zero;
        }
      };
      wBigInt.prototype.isOdd = function() {
        return (this & wBigInt.one) == wBigInt(1);
      };
      wBigInt.prototype.isNegative = function() {
        return this < wBigInt.zero;
      };
      wBigInt.prototype.and = function(m) {
        return this & m;
      };
      wBigInt.prototype.div = function(c) {
        return this / c;
      };
      wBigInt.prototype.mod = function(c) {
        return this % c;
      };
      wBigInt.prototype.pow = function(c) {
        return this ** c;
      };
      wBigInt.prototype.abs = function() {
        return this > wBigInt.zero ? this : -this;
      };
      wBigInt.prototype.modPow = function(e, m) {
        let acc = wBigInt.one;
        let exp = this;
        let rem = e;
        while (rem) {
          if (rem & wBigInt.one) {
            acc = acc * exp % m;
          }
          exp = exp * exp % m;
          rem = rem >> wBigInt.one;
        }
        return acc;
      };
      wBigInt.prototype.greaterOrEquals = function(b) {
        return this >= b;
      };
      wBigInt.prototype.greater = function(b) {
        return this > b;
      };
      wBigInt.prototype.gt = wBigInt.prototype.greater;
      wBigInt.prototype.lesserOrEquals = function(b) {
        return this <= b;
      };
      wBigInt.prototype.lesser = function(b) {
        return this < b;
      };
      wBigInt.prototype.lt = wBigInt.prototype.lesser;
      wBigInt.prototype.equals = function(b) {
        return this == b;
      };
      wBigInt.prototype.eq = wBigInt.prototype.equals;
      wBigInt.prototype.neq = function(b) {
        return this != b;
      };
      wBigInt.prototype.toJSNumber = function() {
        return Number(this);
      };
    } else {
      oldProto = bigInt3.prototype;
      wBigInt = function(a) {
        if (typeof a == "string" && a.slice(0, 2) == "0x") {
          return bigInt3(a.slice(2), 16);
        } else {
          return bigInt3(a);
        }
      };
      wBigInt.one = bigInt3.one;
      wBigInt.zero = bigInt3.zero;
      wBigInt.prototype = oldProto;
      wBigInt.prototype.div = function(c) {
        return this.divide(c);
      };
      wBigInt.genAffine = (q) => {
        const nq = wBigInt.zero.minus(q);
        return (a) => {
          let aux = a;
          if (aux.isNegative()) {
            if (aux.lesserOrEquals(nq)) {
              aux = aux.mod(q);
            }
            if (aux.isNegative()) {
              aux = aux.add(q);
            }
          } else {
            if (aux.greaterOrEquals(q)) {
              aux = aux.mod(q);
            }
          }
          return aux;
        };
      };
      wBigInt.genInverse = (q) => {
        return (a) => a.affine(q).modInv(q);
      };
      wBigInt.genAdd = (q) => {
        if (q) {
          return (a, b) => {
            const r = a.add(b);
            return r.greaterOrEquals(q) ? r.minus(q) : r;
          };
        } else {
          return (a, b) => a.add(b);
        }
      };
      wBigInt.genSub = (q) => {
        if (q) {
          return (a, b) => a.greaterOrEquals(b) ? a.minus(b) : a.minus(b).add(q);
        } else {
          return (a, b) => a.minus(b);
        }
      };
      wBigInt.genNeg = (q) => {
        if (q) {
          return (a) => a.isZero() ? a : q.minus(a);
        } else {
          return (a) => wBigInt.zero.minus(a);
        }
      };
      wBigInt.genMul = (q) => {
        if (q) {
          return (a, b) => a.times(b).mod(q);
        } else {
          return (a, b) => a.times(b);
        }
      };
      wBigInt.genShr = () => {
        return (a, b) => a.shiftRight(wBigInt(b).value);
      };
      wBigInt.genShl = (q) => {
        if (q) {
          return (a, b) => a.shiftLeft(wBigInt(b).value).mod(q);
        } else {
          return (a, b) => a.shiftLeft(wBigInt(b).value);
        }
      };
      wBigInt.genSquare = (q) => {
        if (q) {
          return (a) => a.square().mod(q);
        } else {
          return (a) => a.square();
        }
      };
      wBigInt.genDouble = (q) => {
        if (q) {
          return (a) => a.add(a).mod(q);
        } else {
          return (a) => a.add(a);
        }
      };
      wBigInt.genEquals = (q) => {
        if (q) {
          return (a, b) => a.affine(q).equals(b.affine(q));
        } else {
          return (a, b) => a.equals(b);
        }
      };
      wBigInt.genIsZero = (q) => {
        if (q) {
          return (a) => a.affine(q).isZero();
        } else {
          return (a) => a.isZero();
        }
      };
    }
    var oldProto;
    wBigInt.affine = function(a, q) {
      return wBigInt.genAffine(q)(a);
    };
    wBigInt.prototype.affine = function(q) {
      return wBigInt.affine(this, q);
    };
    wBigInt.inverse = function(a, q) {
      return wBigInt.genInverse(q)(a);
    };
    wBigInt.prototype.inverse = function(q) {
      return wBigInt.genInverse(q)(this);
    };
    wBigInt.add = function(a, b, q) {
      return wBigInt.genAdd(q)(a, b);
    };
    wBigInt.prototype.add = function(a, q) {
      return wBigInt.genAdd(q)(this, a);
    };
    wBigInt.sub = function(a, b, q) {
      return wBigInt.genSub(q)(a, b);
    };
    wBigInt.prototype.sub = function(a, q) {
      return wBigInt.genSub(q)(this, a);
    };
    wBigInt.neg = function(a, q) {
      return wBigInt.genNeg(q)(a);
    };
    wBigInt.prototype.neg = function(q) {
      return wBigInt.genNeg(q)(this);
    };
    wBigInt.mul = function(a, b, q) {
      return wBigInt.genMul(q)(a, b);
    };
    wBigInt.prototype.mul = function(a, q) {
      return wBigInt.genMul(q)(this, a);
    };
    wBigInt.shr = function(a, b, q) {
      return wBigInt.genShr(q)(a, b);
    };
    wBigInt.prototype.shr = function(a, q) {
      return wBigInt.genShr(q)(this, a);
    };
    wBigInt.shl = function(a, b, q) {
      return wBigInt.genShl(q)(a, b);
    };
    wBigInt.prototype.shl = function(a, q) {
      return wBigInt.genShl(q)(this, a);
    };
    wBigInt.equals = function(a, b, q) {
      return wBigInt.genEquals(q)(a, b);
    };
    wBigInt.prototype.equals = function(a, q) {
      return wBigInt.genEquals(q)(this, a);
    };
    wBigInt.square = function(a, q) {
      return wBigInt.genSquare(q)(a);
    };
    wBigInt.prototype.square = function(q) {
      return wBigInt.genSquare(q)(this);
    };
    wBigInt.double = function(a, q) {
      return wBigInt.genDouble(q)(a);
    };
    wBigInt.prototype.double = function(q) {
      return wBigInt.genDouble(q)(this);
    };
    wBigInt.isZero = function(a, q) {
      return wBigInt.genIsZero(q)(a);
    };
    wBigInt.prototype.isZero = function(q) {
      return wBigInt.genIsZero(q)(this);
    };
    wBigInt.leBuff2int = function(buff) {
      let res = wBigInt.zero;
      for (let i = 0; i < buff.length; i++) {
        const n = wBigInt(buff[i]);
        res = res.add(n.shl(i * 8));
      }
      return res;
    };
    wBigInt.leInt2Buff = function(n, len) {
      let r = n;
      let o = 0;
      const buff = Buffer.alloc(len);
      while (r.greater(wBigInt.zero) && o < buff.length) {
        let c = Number(r.and(wBigInt("255")));
        buff[o] = c;
        o++;
        r = r.shr(8);
      }
      if (r.greater(wBigInt.zero)) throw new Error("Number does not feed in buffer");
      return buff;
    };
    wBigInt.prototype.leInt2Buff = function(len) {
      return wBigInt.leInt2Buff(this, len);
    };
    wBigInt.beBuff2int = function(buff) {
      let res = wBigInt.zero;
      for (let i = 0; i < buff.length; i++) {
        const n = wBigInt(buff[buff.length - i - 1]);
        res = res.add(n.shl(i * 8));
      }
      return res;
    };
    wBigInt.beInt2Buff = function(n, len) {
      let r = n;
      let o = len - 1;
      const buff = Buffer.alloc(len);
      while (r.greater(wBigInt.zero) && o >= 0) {
        let c = Number(r.and(wBigInt("255")));
        buff[o] = c;
        o--;
        r = r.shr(8);
      }
      if (r.greater(wBigInt.zero)) throw new Error("Number does not feed in buffer");
      return buff;
    };
    wBigInt.prototype.beInt2Buff = function(len) {
      return wBigInt.beInt2Buff(this, len);
    };
    module2.exports = wBigInt;
  }
});

// ../../snarkjs/src/calculateWitness.js
var require_calculateWitness = __commonJS({
  "../../snarkjs/src/calculateWitness.js"(exports2, module2) {
    var bigInt3 = require_bigint();
    module2.exports = calculateWitness2;
    function calculateWitness2(circuit, inputSignals, options) {
      options = options || {};
      if (!options.logFunction) options.logFunction = console.log;
      const ctx = new RTCtx(circuit, options);
      function iterateSelector(values, sels, cb) {
        if (!Array.isArray(values)) {
          return cb(sels, values);
        }
        for (let i = 0; i < values.length; i++) {
          sels.push(i);
          iterateSelector(values[i], sels, cb);
          sels.pop(i);
        }
      }
      ctx.setSignal("one", [], bigInt3(1));
      for (let c in ctx.notInitSignals) {
        if (ctx.notInitSignals[c] == 0) ctx.triggerComponent(c);
      }
      for (let s in inputSignals) {
        ctx.currentComponent = "main";
        iterateSelector(inputSignals[s], [], function(selector, value) {
          if (typeof value == "undefined") throw new Error("Signal not defined:" + s);
          ctx.setSignal(s, selector, bigInt3(value));
        });
      }
      for (let i = 0; i < circuit.nInputs; i++) {
        const idx = circuit.inputIdx(i);
        if (typeof ctx.witness[idx] == "undefined") {
          throw new Error("Input Signal not assigned: " + circuit.signalNames(idx));
        }
      }
      for (let i = 0; i < ctx.witness.length; i++) {
        if (typeof ctx.witness[i] == "undefined") {
          throw new Error("Signal not assigned: " + circuit.signalNames(i));
        }
        if (options.logOutput) options.logFunction(circuit.signalNames(i) + " --> " + ctx.witness[i].toString());
      }
      return ctx.witness.slice(0, circuit.nVars);
    }
    var RTCtx = class {
      constructor(circuit, options) {
        this.options = options;
        this.scopes = [];
        this.circuit = circuit;
        this.witness = new Array(circuit.nSignals);
        this.notInitSignals = {};
        for (let c in this.circuit.components) {
          this.notInitSignals[c] = this.circuit.components[c].inputSignals;
        }
      }
      _sels2str(sels) {
        let res = "";
        for (let i = 0; i < sels.length; i++) {
          res += `[${sels[i]}]`;
        }
        return res;
      }
      setPin(componentName, componentSels, signalName, signalSels, value) {
        let fullName = componentName == "one" ? "one" : this.currentComponent + "." + componentName;
        fullName += this._sels2str(componentSels) + "." + signalName + this._sels2str(signalSels);
        this.setSignalFullName(fullName, value);
      }
      setSignal(name, sels, value) {
        let fullName = this.currentComponent ? this.currentComponent + "." + name : name;
        fullName += this._sels2str(sels);
        this.setSignalFullName(fullName, value);
      }
      triggerComponent(c) {
        if (this.options.logTrigger) this.options.logFunction("Component Treiggered: " + this.circuit.components[c].name);
        this.notInitSignals[c]--;
        const oldComponent = this.currentComponent;
        this.currentComponent = this.circuit.components[c].name;
        const template = this.circuit.components[c].template;
        const newScope = {};
        for (let p in this.circuit.components[c].params) {
          newScope[p] = this.circuit.components[c].params[p];
        }
        const oldScope = this.scopes;
        this.scopes = [this.scopes[0], newScope];
        this.circuit.templates[template](this);
        this.scopes = oldScope;
        this.currentComponent = oldComponent;
        if (this.options.logTrigger) this.options.logFunction("End Component Treiggered: " + this.circuit.components[c].name);
      }
      callFunction(functionName, params) {
        const newScope = {};
        for (let p = 0; p < this.circuit.functions[functionName].params.length; p++) {
          const paramName = this.circuit.functions[functionName].params[p];
          newScope[paramName] = params[p];
        }
        const oldScope = this.scopes;
        this.scopes = [this.scopes[0], newScope];
        const res = this.circuit.functions[functionName].func(this);
        this.scopes = oldScope;
        return res;
      }
      setSignalFullName(fullName, value) {
        if (this.options.logSet) this.options.logFunction("set " + fullName + " <-- " + value.toString());
        const sId = this.circuit.getSignalIdx(fullName);
        let firstInit = false;
        if (typeof this.witness[sId] == "undefined") {
          firstInit = true;
        }
        this.witness[sId] = bigInt3(value);
        const callComponents = [];
        for (let i = 0; i < this.circuit.signals[sId].triggerComponents.length; i++) {
          var idCmp = this.circuit.signals[sId].triggerComponents[i];
          if (firstInit) this.notInitSignals[idCmp]--;
          callComponents.push(idCmp);
        }
        callComponents.map((c) => {
          if (this.notInitSignals[c] == 0) this.triggerComponent(c);
        });
        return this.witness[sId];
      }
      setVar(name, sels, value) {
        function setVarArray(a, sels2, value2) {
          if (sels2.length == 1) {
            a[sels2[0]] = value2;
          } else {
            if (typeof a[sels2[0]] == "undefined") a[sels2[0]] = [];
            setVarArray(a[sels2[0]], sels2.slice(1), value2);
          }
        }
        const scope = this.scopes[this.scopes.length - 1];
        if (sels.length == 0) {
          scope[name] = value;
        } else {
          if (typeof scope[name] == "undefined") scope[name] = [];
          setVarArray(scope[name], sels, value);
        }
        return value;
      }
      getVar(name, sels) {
        function select(a, sels2) {
          return sels2.length == 0 ? a : select(a[sels2[0]], sels2.slice(1));
        }
        for (let i = this.scopes.length - 1; i >= 0; i--) {
          if (typeof this.scopes[i][name] != "undefined") return select(this.scopes[i][name], sels);
        }
        throw new Error("Variable not defined: " + name);
      }
      getSignal(name, sels) {
        let fullName = name == "one" ? "one" : this.currentComponent + "." + name;
        fullName += this._sels2str(sels);
        return this.getSignalFullName(fullName);
      }
      getPin(componentName, componentSels, signalName, signalSels) {
        let fullName = componentName == "one" ? "one" : this.currentComponent + "." + componentName;
        fullName += this._sels2str(componentSels) + "." + signalName + this._sels2str(signalSels);
        return this.getSignalFullName(fullName);
      }
      getSignalFullName(fullName) {
        const sId = this.circuit.getSignalIdx(fullName);
        if (typeof this.witness[sId] == "undefined") {
          throw new Error("Signal not initialized: " + fullName);
        }
        if (this.options.logGet) this.options.logFunction("get --->" + fullName + " = " + this.witness[sId].toString());
        return this.witness[sId];
      }
      assert(a, b, errStr) {
        const ba = bigInt3(a);
        const bb = bigInt3(b);
        if (!ba.equals(bb)) {
          throw new Error("Constraint doesn't match " + this.currentComponent + ": " + errStr + " -> " + ba.toString() + " != " + bb.toString());
        }
      }
    };
  }
});

// ../../snarkjs/src/circuit.js
var require_circuit = __commonJS({
  "../../snarkjs/src/circuit.js"(exports, module) {
    var bigInt = require_bigint();
    var __P__ = bigInt("21888242871839275222246405745257275088548364400416034343698204186575808495617");
    var __MASK__ = bigInt("28948022309329048855892746252171976963317496166410141009864396001978282409983");
    var calculateWitness = require_calculateWitness();
    module.exports = class Circuit {
      constructor(circuitDef) {
        this.nPubInputs = circuitDef.nPubInputs;
        this.nPrvInputs = circuitDef.nPrvInputs;
        this.nInputs = circuitDef.nInputs;
        this.nOutputs = circuitDef.nOutputs;
        this.nVars = circuitDef.nVars;
        this.nSignals = circuitDef.nSignals;
        this.nConstants = circuitDef.nConstants;
        this.nConstraints = circuitDef.constraints.length;
        this.signalName2Idx = circuitDef.signalName2Idx;
        this.components = circuitDef.components;
        this.componentName2Idx = circuitDef.componentName2Idx;
        this.signals = circuitDef.signals;
        this.constraints = circuitDef.constraints;
        this.templates = {};
        for (let t in circuitDef.templates) {
          this.templates[t] = eval(" const __f= " + circuitDef.templates[t] + "\n__f");
        }
        this.functions = {};
        for (let f in circuitDef.functions) {
          this.functions[f] = {
            params: circuitDef.functions[f].params,
            func: eval(" const __f= " + circuitDef.functions[f].func + "\n__f;")
          };
        }
      }
      calculateWitness(input, log) {
        return calculateWitness(this, input, log);
      }
      checkWitness(w) {
        const evalLC = (lc, w2) => {
          let acc = bigInt(0);
          for (let k in lc) {
            acc = acc.add(bigInt(w2[k]).mul(bigInt(lc[k]))).mod(__P__);
          }
          return acc;
        };
        const checkConstraint = (ct, w2) => {
          const a = evalLC(ct[0], w2);
          const b = evalLC(ct[1], w2);
          const c = evalLC(ct[2], w2);
          const res = a.mul(b).sub(c).affine(__P__);
          if (!res.isZero()) return false;
          return true;
        };
        for (let i = 0; i < this.constraints.length; i++) {
          if (!checkConstraint(this.constraints[i], w)) {
            this.printCostraint(this.constraints[i]);
            return false;
          }
        }
        return true;
      }
      printCostraint(c) {
        const lc2str = (lc) => {
          let S2 = "";
          for (let k in lc) {
            let name = this.signals[k].names[0];
            if (name == "one") name = "";
            let v = bigInt(lc[k]);
            let vs;
            if (!v.lesserOrEquals(__P__.shr(bigInt(1)))) {
              v = __P__.sub(v);
              vs = "-" + v.toString();
            } else {
              if (S2 != "") {
                vs = "+" + v.toString();
              } else {
                vs = "";
              }
              if (vs != "1") {
                vs = vs + v.toString();
                ;
              }
            }
            S2 = S2 + " " + vs + name;
          }
          return S2;
        };
        const S = `[ ${lc2str(c[0])} ] * [ ${lc2str(c[1])} ] - [ ${lc2str(c[2])} ] = 0`;
        console.log(S);
      }
      printConstraints() {
        for (let i = 0; i < this.constraints.length; i++) {
          this.printCostraint(this.constraints[i]);
        }
      }
      getSignalIdx(name) {
        if (typeof this.signalName2Idx[name] != "undefined") return this.signalName2Idx[name];
        if (!isNaN(name)) return Number(name);
        throw new Error("Invalid signal identifier: " + name);
      }
      // returns the index of the i'th output
      outputIdx(i) {
        if (i >= this.nOutputs) throw new Error("Accessing an invalid output: " + i);
        return i + 1;
      }
      // returns the index of the i'th input
      inputIdx(i) {
        if (i >= this.nInputs) throw new Error("Accessing an invalid input: " + i);
        return this.nOutputs + 1 + i;
      }
      // returns the index of the i'th public input
      pubInputIdx(i) {
        if (i >= this.nPubInputs) throw new Error("Accessing an invalid pubInput: " + i);
        return this.inputIdx(i);
      }
      // returns the index of the i'th private input
      prvInputIdx(i) {
        if (i >= this.nPrvInputs) throw new Error("Accessing an invalid prvInput: " + i);
        return this.inputIdx(this.nPubInputs + i);
      }
      // returns the index of the i'th variable
      varIdx(i) {
        if (i >= this.nVars) throw new Error("Accessing an invalid variable: " + i);
        return i;
      }
      // returns the index of the i'th constant
      constantIdx(i) {
        if (i >= this.nConstants) throw new Error("Accessing an invalid constant: " + i);
        return this.nVars + i;
      }
      // returns the index of the i'th signal
      signalIdx(i) {
        if (i >= this.nSignls) throw new Error("Accessing an invalid signal: " + i);
        return i;
      }
      signalNames(i) {
        return this.signals[this.getSignalIdx(i)].names.join(", ");
      }
      a(constraint, signalIdx) {
        return bigInt(this.constraints[constraint][0][signalIdx] || 0);
      }
      b(constraint, signalIdx) {
        return bigInt(this.constraints[constraint][1][signalIdx] || 0);
      }
      c(constraint, signalIdx) {
        return bigInt(this.constraints[constraint][2][signalIdx] || 0);
      }
    };
  }
});

// ../tools/stringifybigint.js
var require_stringifybigint = __commonJS({
  "../tools/stringifybigint.js"(exports2, module2) {
    var bigInt3 = require_BigInteger();
    module2.exports.stringifyBigInts = stringifyBigInts3;
    module2.exports.unstringifyBigInts = unstringifyBigInts3;
    module2.exports.hexifyBigInts = hexifyBigInts2;
    module2.exports.unhexifyBigInts = unhexifyBigInts2;
    function stringifyBigInts3(o) {
      if (typeof o == "bigint" || o instanceof bigInt3) {
        return o.toString(10);
      } else if (Array.isArray(o)) {
        return o.map(stringifyBigInts3);
      } else if (typeof o == "object") {
        const res = {};
        for (let k in o) {
          res[k] = stringifyBigInts3(o[k]);
        }
        return res;
      } else {
        return o;
      }
    }
    function unstringifyBigInts3(o) {
      if (typeof o == "string" && /^[0-9]+$/.test(o)) {
        return bigInt3(o);
      } else if (Array.isArray(o)) {
        return o.map(unstringifyBigInts3);
      } else if (typeof o == "object" && !(o instanceof bigInt3)) {
        const res = {};
        for (let k in o) {
          res[k] = unstringifyBigInts3(o[k]);
        }
        return res;
      } else {
        return o;
      }
    }
    function hexifyBigInts2(o) {
      if (typeof o === "bigInt" || o instanceof bigInt3) {
        let str = o.toString(16);
        while (str.length < 64) str = "0" + str;
        str = "0x" + str;
        return str;
      } else if (Array.isArray(o)) {
        return o.map(hexifyBigInts2);
      } else if (typeof o == "object") {
        const res = {};
        for (let k in o) {
          res[k] = hexifyBigInts2(o[k]);
        }
        return res;
      } else {
        return o;
      }
    }
    function unhexifyBigInts2(o) {
      if (typeof o == "string" && /^0x[0-9a-fA-F]+$/.test(o)) {
        return bigInt3(o);
      } else if (Array.isArray(o)) {
        return o.map(unhexifyBigInts2);
      } else if (typeof o == "object") {
        const res = {};
        for (let k in o) {
          res[k] = unhexifyBigInts2(o[k]);
        }
        return res;
      } else {
        return o;
      }
    }
  }
});

// ../../snarkjs/src/stringifybigint.js
var require_stringifybigint2 = __commonJS({
  "../../snarkjs/src/stringifybigint.js"(exports2, module2) {
    var bigInt3 = require_bigint();
    module2.exports.stringifyBigInts = stringifyBigInts3;
    module2.exports.unstringifyBigInts = unstringifyBigInts3;
    function stringifyBigInts3(o) {
      if (typeof o == "bigint" || o.isZero !== void 0) {
        return o.toString(10);
      } else if (Array.isArray(o)) {
        return o.map(stringifyBigInts3);
      } else if (typeof o == "object") {
        const res = {};
        for (let k in o) {
          res[k] = stringifyBigInts3(o[k]);
        }
        return res;
      } else {
        return o;
      }
    }
    function unstringifyBigInts3(o) {
      if (typeof o == "string" && /^[0-9]+$/.test(o)) {
        return bigInt3(o);
      } else if (Array.isArray(o)) {
        return o.map(unstringifyBigInts3);
      } else if (typeof o == "object") {
        const res = {};
        for (let k in o) {
          res[k] = unstringifyBigInts3(o[k]);
        }
        return res;
      } else {
        return o;
      }
    }
  }
});

// utils.js
var buildGroth16 = require_groth16();
var bigInt2 = require_BigInteger();
var Circuit = require_circuit();
var bigInt22 = require_bigint();
var hexifyBigInts = require_stringifybigint().hexifyBigInts;
var unhexifyBigInts = require_stringifybigint().unhexifyBigInts;
var stringifyBigInts = require_stringifybigint().stringifyBigInts;
var unstringifyBigInts = require_stringifybigint().unstringifyBigInts;
var stringifyBigInts2 = require_stringifybigint2().stringifyBigInts;
var unstringifyBigInts2 = require_stringifybigint2().unstringifyBigInts;
function convertWitness(witness) {
  const buffLen = witness.length * 32;
  const buff = new ArrayBuffer(buffLen);
  const h = {
    dataView: new DataView(buff),
    offset: 0
  };
  const mask = bigInt22(4294967295);
  for (let i = 0; i < witness.length; i++) {
    for (let j = 0; j < 8; j++) {
      const v = Number(witness[i].shr(j * 32).and(mask));
      h.dataView.setUint32(h.offset, v, true);
      h.offset += 4;
    }
  }
  return buff;
}
function toHex32(number) {
  let str = number.toString(16);
  while (str.length < 64) str = "0" + str;
  return str;
}
function toSolidityInput(proof) {
  const flatProof = unstringifyBigInts([
    proof.pi_a[0],
    proof.pi_a[1],
    proof.pi_b[0][1],
    proof.pi_b[0][0],
    proof.pi_b[1][1],
    proof.pi_b[1][0],
    proof.pi_c[0],
    proof.pi_c[1]
  ]);
  const result = {
    proof: "0x" + flatProof.map((x) => toHex32(x)).join("")
  };
  if (proof.publicSignals) {
    result.publicSignals = hexifyBigInts(unstringifyBigInts(proof.publicSignals));
  }
  return result;
}
function genWitness(input, circuit_json) {
  const circuit = new Circuit(unstringifyBigInts2(circuit_json));
  const witness = circuit.calculateWitness(unstringifyBigInts2(input));
  const publicSignals = witness.slice(1, circuit.nPubInputs + circuit.nOutputs + 1);
  return { witness, publicSignals };
}
async function genWitnessAndProveAsync(input, circuit_json, provingKey) {
  const groth16 = await buildGroth16();
  const witnessData = genWitness(input, circuit_json);
  const witnessBin = convertWitness(witnessData.witness);
  const result = await groth16.proof(witnessBin, provingKey);
  result.publicSignals = stringifyBigInts2(witnessData.publicSignals);
  result.solidity = toSolidityInput(result);
  return result;
}

// Sync wrapper
const { Worker } = require('node:worker_threads');
const { TextDecoder } = require('node:util');
function genWitnessAndProveSync(input, circuit_json, provingKey) {
  const timeoutMs = 120_000; // 120 seconds
  const capacity = 8 * 1024 * 1024;  // 8MB
  // ctrl[0] = status, 0 = busy, 1 = success, 2 = error, 3 = overflow
  // ctrl[1] = Valid length of data buffer (for success, error, overflow)
  const ctrlSAB = new SharedArrayBuffer(8);
  const ctrl = new Int32Array(ctrlSAB);
  const dataSAB = new SharedArrayBuffer(capacity);
  const data = new Uint8Array(dataSAB);
  const workerCode = `
const { workerData } = require('node:worker_threads');
const { TextEncoder } = require('node:util');
const ctrl = new Int32Array(workerData.ctrlSAB);
const data = new Uint8Array(workerData.dataSAB);
const encoder = new TextEncoder();
const writeOk = (obj) => {
  const json  = JSON.stringify(obj, (_,v)=> typeof v === 'bigint' ? v.toString() : v);
  const bytes = encoder.encode(json);
  if (bytes.length > data.length) {
    Atomics.store(ctrl, 1, bytes.length);  // Required length
    Atomics.store(ctrl, 0, 3);  // overflow
  } else {
    data.set(bytes.subarray(0, bytes.length));
    Atomics.store(ctrl, 1, bytes.length);
    Atomics.store(ctrl, 0, 1);  // success
  }
  Atomics.notify(ctrl, 0);
};
const writeErr = (e) => {
  const msg   = String(e && e.stack || e);
  const bytes = encoder.encode(msg);
  const n = Math.min(bytes.length, data.length);
  data.set(bytes.subarray(0, n));
  Atomics.store(ctrl, 1, n);
  Atomics.store(ctrl, 0, 2);
  Atomics.notify(ctrl, 0);
};
(async () => {
  try {
    // Key point: require "this module itself" in the worker, only call the async version to avoid recursive into the sync wrapper
    const mod = require(workerData.modulePath);
    const { input, circuit_json, provingKey } = workerData.args;
    const result = await mod.genWitnessAndProveAsync(input, circuit_json, provingKey);
    writeOk(result);
  } catch (e) {
    writeErr(e);
  }
})();
process.on('uncaughtException',  writeErr);
process.on('unhandledRejection', writeErr);
  `;
  const w = new Worker(workerCode, {
    eval: true,
    workerData: {
      ctrlSAB, dataSAB,
      modulePath: __filename,
      args: { input, circuit_json, provingKey }
    }
  });
  // Block current thread until worker notifies (or timeout)
  const res = Atomics.wait(ctrl, 0, 0, timeoutMs);
  try {
    if (res === 'timed-out') throw new Error('genWitnessAndProveSync: worker timed out');
    const status = Atomics.load(ctrl, 0);
    const len = Atomics.load(ctrl, 1);
    const text   = new TextDecoder().decode(new Uint8Array(dataSAB, 0, len));
    if (status === 1) {
      return JSON.parse(text);  // Succeed
    } else if (status === 2) {
      throw new Error(text || 'worker failed');
    } else if (status === 3) {
      throw new Error('Result too large for SharedArrayBuffer (need ' + len + ' bytes, have ' + (data.byteLength) + ')');
    }
    throw new Error('Unknown worker status: ' + status);
  } finally {
    w.terminate();
  }
}

const fs = require('fs');
const path = require('path');
const circuit_json = require(path.resolve(__dirname, '..', 'tornado', 'circuit.json'));
const proving_key = fs.readFileSync(path.resolve(__dirname, '..', 'tornado', 'proving_key.bin')).buffer;
function prove(input) {
  return genWitnessAndProveSync(input, circuit_json, proving_key);
}

module.exports = { prove, genWitnessAndProveAsync };

if (require.main === module) {
  const input_obj = JSON.parse(process.argv[2]);
  let result = genWitnessAndProveSync(input_obj, circuit_json, proving_key);
  console.log(JSON.stringify(result))
}
