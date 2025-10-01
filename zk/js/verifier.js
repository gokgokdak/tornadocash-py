var __getOwnPropNames = Object.getOwnPropertyNames;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};

// ../node_modules/big-integer/BigInteger.js
var require_BigInteger = __commonJS({
  "../node_modules/big-integer/BigInteger.js"(exports2, module2) {
    var bigInt = function(undefined) {
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
        var nPrev = n.prev(), b = nPrev, r = 0, d, t, i2, x;
        while (b.isEven()) b = b.divide(2), r++;
        next: for (i2 = 0; i2 < a.length; i2++) {
          if (n.lesser(a[i2])) continue;
          x = bigInt(a[i2]).modPow(b, n);
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
        if (isPrime !== undefined) return isPrime;
        var n = this.abs();
        var bits = n.bitLength();
        if (bits <= 64)
          return millerRabinTest(n, [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]);
        var logN = Math.log(2) * bits.toJSNumber();
        var t = Math.ceil(strict === true ? 2 * Math.pow(logN, 2) : logN);
        for (var a = [], i2 = 0; i2 < t; i2++) {
          a.push(bigInt(i2 + 2));
        }
        return millerRabinTest(n, a);
      };
      NativeBigInt.prototype.isPrime = SmallInteger.prototype.isPrime = BigInteger.prototype.isPrime;
      BigInteger.prototype.isProbablePrime = function(iterations) {
        var isPrime = isBasicPrime(this);
        if (isPrime !== undefined) return isPrime;
        var n = this.abs();
        var t = iterations === undefined ? 5 : iterations;
        for (var a = [], i2 = 0; i2 < t; i2++) {
          a.push(bigInt.randBetween(2, n.minus(2)));
        }
        return millerRabinTest(n, a);
      };
      NativeBigInt.prototype.isProbablePrime = SmallInteger.prototype.isProbablePrime = BigInteger.prototype.isProbablePrime;
      BigInteger.prototype.modInv = function(n) {
        var t = bigInt.zero, newT = bigInt.one, r = parseValue(n), newR = this.abs(), q, lastT, lastR;
        while (!newR.isZero()) {
          q = r.divide(newR);
          lastT = t;
          lastR = r;
          t = newT;
          r = newR;
          newT = lastT.subtract(q.multiply(newT));
          newR = lastR.subtract(q.multiply(newR));
        }
        if (!r.isUnit()) throw new Error(this.toString() + " and " + n.toString() + " are not co-prime");
        if (t.compare(0) === -1) {
          t = t.add(n);
        }
        if (this.isNegative()) {
          return t.negate();
        }
        return t;
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
        var sum = fn(xSign ? 1 : 0, ySign ? 1 : 0) !== 0 ? bigInt(-1) : bigInt(0);
        for (var i2 = result.length - 1; i2 >= 0; i2 -= 1) {
          sum = sum.multiply(highestPower2).add(bigInt(result[i2]));
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
          var t = p.multiply(base);
          return t.compareTo(value) <= 0 ? { p: t, e: e * 2 + 1 } : { p, e: e * 2 };
        }
        return { p: bigInt(1), e: 0 };
      }
      BigInteger.prototype.bitLength = function() {
        var n = this;
        if (n.compareTo(bigInt(0)) < 0) {
          n = n.negate().subtract(bigInt(1));
        }
        if (n.compareTo(bigInt(0)) === 0) {
          return bigInt(0);
        }
        return bigInt(integerLogarithm(n, bigInt(2)).e).add(bigInt(1));
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
        var c = Integer[1], d, t;
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
            t = b;
            b = a;
            a = t;
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
      function randBetween(a, b) {
        a = parseValue(a);
        b = parseValue(b);
        var low = min(a, b), high = max(a, b);
        var range = high.subtract(low).add(1);
        if (range.isSmall) return low.add(Math.floor(Math.random() * range));
        var digits = toBase(range, BASE).value;
        var result = [], restricted = true;
        for (var i2 = 0; i2 < digits.length; i2++) {
          var top = restricted ? digits[i2] : BASE;
          var digit = truncate(Math.random() * top);
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
        base = bigInt(base);
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
        if (radix === undefined) radix = 10;
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
        if (radix === undefined) radix = 10;
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
        var isValid2 = /^([0-9][0-9]*)$/.test(v);
        if (!isValid2) throw new Error("Invalid integer: " + v);
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
    }();
    if (typeof module2 !== "undefined" && module2.hasOwnProperty("exports")) {
      module2.exports = bigInt;
    }
    if (typeof define === "function" && define.amd) {
      define("big-integer", [], function() {
        return bigInt;
      });
    }
  }
});

// bigint.js
var require_bigint = __commonJS({
  "bigint.js"(exports2, module2) {
    var bigInt = require_BigInteger();
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
          let t = wBigInt.zero;
          let r = q;
          let newt = wBigInt.one;
          let newr = wBigInt.affine(a, q);
          while (newr != wBigInt.zero) {
            let q2 = r / newr;
            [t, newt] = [newt, t - q2 * newt];
            [r, newr] = [newr, r - q2 * newr];
          }
          if (t < wBigInt.zero) t += q;
          return t;
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
      oldProto = bigInt.prototype;
      wBigInt = function(a) {
        if (typeof a == "string" && a.slice(0, 2) == "0x") {
          return bigInt(a.slice(2), 16);
        } else {
          return bigInt(a);
        }
      };
      wBigInt.one = bigInt.one;
      wBigInt.zero = bigInt.zero;
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

// futils.js
var require_futils = __commonJS({
  "futils.js"(exports2) {
    var bigInt = require_bigint();
    exports2.mulScalar = (F, base, e) => {
      let res = F.zero;
      let rem = bigInt(e);
      let exp = base;
      while (!rem.isZero()) {
        if (rem.isOdd()) {
          res = F.add(res, exp);
        }
        exp = F.double(exp);
        rem = rem.shr(1);
      }
      return res;
    };
    exports2.exp = (F, base, e) => {
      let res = F.one;
      let rem = bigInt(e);
      let exp = base;
      while (!rem.isZero()) {
        if (rem.isOdd()) {
          res = F.mul(res, exp);
        }
        exp = F.square(exp);
        rem = rem.shr(1);
      }
      return res;
    };
  }
});

// zqfield.js
var require_zqfield = __commonJS({
  "zqfield.js"(exports2, module2) {
    var bigInt = require_bigint();
    var fUtils = require_futils();
    function getRandomByte() {
      if (typeof window !== "undefined") {
        if (typeof window.crypto !== "undefined") {
          let array = new Uint8Array(1);
          window.crypto.getRandomValues(array);
          return array[0];
        } else {
          return Math.floor(Math.random() * 256);
        }
      } else {
        return require("crypto").randomBytes(1)[0];
      }
    }
    var ZqField = class {
      constructor(q) {
        this.q = bigInt(q);
        this.zero = bigInt.zero;
        this.one = bigInt.one;
        this.minusone = this.q.sub(this.one);
        this.add = bigInt.genAdd();
        this.double = bigInt.genDouble();
        this.sub = bigInt.genSub();
        this.neg = bigInt.genNeg();
        this.mul = bigInt.genMul(q);
        this.inverse = bigInt.genInverse(q);
        this.square = bigInt.genSquare(q);
        this.equals = bigInt.genEquals(q);
        this.affine = bigInt.genAffine(q);
        this.isZero = bigInt.genIsZero(q);
        this.two = this.add(this.one, this.one);
        this.twoinv = this.inverse(this.two);
        const e = this.minusone.shr(this.one);
        this.nqr = this.two;
        let r = this.exp(this.nqr, e);
        while (!r.equals(this.minusone)) {
          this.nqr = this.nqr.add(this.one);
          r = this.exp(this.nqr, e);
        }
        this.s = this.zero;
        this.t = this.minusone;
        while (!this.t.isOdd()) {
          this.s = this.s.add(this.one);
          this.t = this.t.shr(this.one);
        }
        this.nqr_to_t = this.exp(this.nqr, this.t);
      }
      copy(a) {
        return bigInt(a);
      }
      div(a, b) {
        return this.mul(a, this.inverse(b));
      }
      mulScalar(base, e) {
        return this.mul(base, bigInt(e));
      }
      exp(base, e) {
        return fUtils.exp(this, base, e);
      }
      toString(a) {
        const ca = this.affine(a);
        return `"0x${ca.toString(16)}"`;
      }
      random() {
        let res = bigInt(0);
        let n = bigInt(this.q);
        while (!n.isZero()) {
          res = res.shl(8).add(bigInt(getRandomByte()));
          n = n.shr(8);
        }
        return res;
      }
      sqrt(n) {
        n = this.affine(n);
        if (n.equals(this.zero)) return this.zero;
        const res = this.exp(n, this.minusone.shr(this.one));
        if (!res.equals(this.one)) return null;
        let m = parseInt(this.s);
        let c = this.nqr_to_t;
        let t = this.exp(n, this.t);
        let r = this.exp(n, this.add(this.t, this.one).shr(this.one));
        while (!t.equals(this.one)) {
          let sq = this.square(t);
          let i = 1;
          while (!sq.equals(this.one)) {
            i++;
            sq = this.square(sq);
          }
          let b = c;
          for (let j = 0; j < m - i - 1; j++) b = this.square(b);
          m = i;
          c = this.square(b);
          t = this.mul(t, c);
          r = this.mul(r, b);
        }
        if (r.greater(this.q.shr(this.one))) {
          r = this.neg(r);
        }
        return r;
      }
    };
    module2.exports = ZqField;
  }
});

// f2field.js
var require_f2field = __commonJS({
  "f2field.js"(exports2, module2) {
    var fUtils = require_futils();
    var F2Field = class {
      constructor(F, nonResidue) {
        this.F = F;
        this.zero = [this.F.zero, this.F.zero];
        this.one = [this.F.one, this.F.zero];
        this.nonResidue = nonResidue;
      }
      _mulByNonResidue(a) {
        return this.F.mul(this.nonResidue, a);
      }
      copy(a) {
        return [this.F.copy(a[0]), this.F.copy(a[1])];
      }
      add(a, b) {
        return [
          this.F.add(a[0], b[0]),
          this.F.add(a[1], b[1])
        ];
      }
      double(a) {
        return this.add(a, a);
      }
      sub(a, b) {
        return [
          this.F.sub(a[0], b[0]),
          this.F.sub(a[1], b[1])
        ];
      }
      neg(a) {
        return this.sub(this.zero, a);
      }
      mul(a, b) {
        const aA = this.F.mul(a[0], b[0]);
        const bB = this.F.mul(a[1], b[1]);
        return [
          this.F.add(aA, this._mulByNonResidue(bB)),
          this.F.sub(
            this.F.mul(
              this.F.add(a[0], a[1]),
              this.F.add(b[0], b[1])
            ),
            this.F.add(aA, bB)
          )
        ];
      }
      inverse(a) {
        const t0 = this.F.square(a[0]);
        const t1 = this.F.square(a[1]);
        const t2 = this.F.sub(t0, this._mulByNonResidue(t1));
        const t3 = this.F.inverse(t2);
        return [
          this.F.mul(a[0], t3),
          this.F.neg(this.F.mul(a[1], t3))
        ];
      }
      div(a, b) {
        return this.mul(a, this.inverse(b));
      }
      square(a) {
        const ab = this.F.mul(a[0], a[1]);
        return [
          this.F.sub(
            this.F.mul(
              this.F.add(a[0], a[1]),
              this.F.add(
                a[0],
                this._mulByNonResidue(a[1])
              )
            ),
            this.F.add(
              ab,
              this._mulByNonResidue(ab)
            )
          ),
          this.F.add(ab, ab)
        ];
      }
      isZero(a) {
        return this.F.isZero(a[0]) && this.F.isZero(a[1]);
      }
      equals(a, b) {
        return this.F.equals(a[0], b[0]) && this.F.equals(a[1], b[1]);
      }
      affine(a) {
        return [this.F.affine(a[0]), this.F.affine(a[1])];
      }
      mulScalar(base, e) {
        return fUtils.mulScalar(this, base, e);
      }
      exp(base, e) {
        return fUtils.exp(this, base, e);
      }
      toString(a) {
        const cp = this.affine(a);
        return `[ ${this.F.toString(cp[0])} , ${this.F.toString(cp[1])} ]`;
      }
    };
    module2.exports = F2Field;
  }
});

// f3field.js
var require_f3field = __commonJS({
  "f3field.js"(exports2, module2) {
    var fUtils = require_futils();
    var F3Field = class {
      constructor(F, nonResidue) {
        this.F = F;
        this.zero = [this.F.zero, this.F.zero, this.F.zero];
        this.one = [this.F.one, this.F.zero, this.F.zero];
        this.nonResidue = nonResidue;
      }
      _mulByNonResidue(a) {
        return this.F.mul(this.nonResidue, a);
      }
      copy(a) {
        return [this.F.copy(a[0]), this.F.copy(a[1]), this.F.copy(a[2])];
      }
      add(a, b) {
        return [
          this.F.add(a[0], b[0]),
          this.F.add(a[1], b[1]),
          this.F.add(a[2], b[2])
        ];
      }
      double(a) {
        return this.add(a, a);
      }
      sub(a, b) {
        return [
          this.F.sub(a[0], b[0]),
          this.F.sub(a[1], b[1]),
          this.F.sub(a[2], b[2])
        ];
      }
      neg(a) {
        return this.sub(this.zero, a);
      }
      mul(a, b) {
        const aA = this.F.mul(a[0], b[0]);
        const bB = this.F.mul(a[1], b[1]);
        const cC = this.F.mul(a[2], b[2]);
        return [
          this.F.add(
            aA,
            this._mulByNonResidue(
              this.F.sub(
                this.F.mul(
                  this.F.add(a[1], a[2]),
                  this.F.add(b[1], b[2])
                ),
                this.F.add(bB, cC)
              )
            )
          ),
          // aA + non_residue*((b+c)*(B+C)-bB-cC),
          this.F.add(
            this.F.sub(
              this.F.mul(
                this.F.add(a[0], a[1]),
                this.F.add(b[0], b[1])
              ),
              this.F.add(aA, bB)
            ),
            this._mulByNonResidue(cC)
          ),
          // (a+b)*(A+B)-aA-bB+non_residue*cC
          this.F.add(
            this.F.sub(
              this.F.mul(
                this.F.add(a[0], a[2]),
                this.F.add(b[0], b[2])
              ),
              this.F.add(aA, cC)
            ),
            bB
          )
        ];
      }
      inverse(a) {
        const t0 = this.F.square(a[0]);
        const t1 = this.F.square(a[1]);
        const t2 = this.F.square(a[2]);
        const t3 = this.F.mul(a[0], a[1]);
        const t4 = this.F.mul(a[0], a[2]);
        const t5 = this.F.mul(a[1], a[2]);
        const c0 = this.F.sub(t0, this._mulByNonResidue(t5));
        const c1 = this.F.sub(this._mulByNonResidue(t2), t3);
        const c2 = this.F.sub(t1, t4);
        const t6 = this.F.inverse(
          this.F.add(
            this.F.mul(a[0], c0),
            this._mulByNonResidue(
              this.F.add(
                this.F.mul(a[2], c1),
                this.F.mul(a[1], c2)
              )
            )
          )
        );
        return [
          this.F.mul(t6, c0),
          // t6*c0
          this.F.mul(t6, c1),
          // t6*c1
          this.F.mul(t6, c2)
        ];
      }
      div(a, b) {
        return this.mul(a, this.inverse(b));
      }
      square(a) {
        const s0 = this.F.square(a[0]);
        const ab = this.F.mul(a[0], a[1]);
        const s1 = this.F.add(ab, ab);
        const s2 = this.F.square(
          this.F.add(this.F.sub(a[0], a[1]), a[2])
        );
        const bc = this.F.mul(a[1], a[2]);
        const s3 = this.F.add(bc, bc);
        const s4 = this.F.square(a[2]);
        return [
          this.F.add(
            s0,
            this._mulByNonResidue(s3)
          ),
          // s0 + non_residue * s3,
          this.F.add(
            s1,
            this._mulByNonResidue(s4)
          ),
          // s1 + non_residue * s4,
          this.F.sub(
            this.F.add(this.F.add(s1, s2), s3),
            this.F.add(s0, s4)
          )
        ];
      }
      isZero(a) {
        return this.F.isZero(a[0]) && this.F.isZero(a[1]) && this.F.isZero(a[2]);
      }
      equals(a, b) {
        return this.F.equals(a[0], b[0]) && this.F.equals(a[1], b[1]) && this.F.equals(a[2], b[2]);
      }
      affine(a) {
        return [this.F.affine(a[0]), this.F.affine(a[1]), this.F.affine(a[2])];
      }
      mulScalar(base, e) {
        return fUtils.mulScalar(this, base, e);
      }
      exp(base, e) {
        return fUtils.exp(this, base, e);
      }
      toString(a) {
        const cp = this.affine(a);
        return `[ ${this.F.toString(cp[0])} , ${this.F.toString(cp[1])}, ${this.F.toString(cp[2])} ]`;
      }
    };
    module2.exports = F3Field;
  }
});

// gcurve.js
var require_gcurve = __commonJS({
  "gcurve.js"(exports2, module2) {
    var fUtils = require_futils();
    var GCurve = class {
      constructor(F, g) {
        this.F = F;
        this.g = [F.copy(g[0]), F.copy(g[1])];
        if (this.g.length == 2) this.g[2] = this.F.one;
        this.zero = [this.F.zero, this.F.one, this.F.zero];
      }
      isZero(p) {
        // Check if p is undefined
        if (p === undefined) {
          console.log("Warning: Point is undefined, returning true for isZero check.");
        }
        return this.F.isZero(p[2]);
      }
      add(p1, p2) {
        const F = this.F;
        if (this.isZero(p1)) return p2;
        if (this.isZero(p2)) return p1;
        const res = new Array(3);
        const Z1Z1 = F.square(p1[2]);
        const Z2Z2 = F.square(p2[2]);
        const U1 = F.mul(p1[0], Z2Z2);
        const U2 = F.mul(p2[0], Z1Z1);
        const Z1_cubed = F.mul(p1[2], Z1Z1);
        const Z2_cubed = F.mul(p2[2], Z2Z2);
        const S1 = F.mul(p1[1], Z2_cubed);
        const S2 = F.mul(p2[1], Z1_cubed);
        if (F.equals(U1, U2) && F.equals(S1, S2)) {
          return this.double(p1);
        }
        const H = F.sub(U2, U1);
        const S2_minus_S1 = F.sub(S2, S1);
        const I = F.square(F.add(H, H));
        const J = F.mul(H, I);
        const r = F.add(S2_minus_S1, S2_minus_S1);
        const V = F.mul(U1, I);
        res[0] = F.sub(
          F.sub(F.square(r), J),
          F.add(V, V)
        );
        const S1_J = F.mul(S1, J);
        res[1] = F.sub(
          F.mul(r, F.sub(V, res[0])),
          F.add(S1_J, S1_J)
        );
        res[2] = F.mul(
          H,
          F.sub(
            F.square(F.add(p1[2], p2[2])),
            F.add(Z1Z1, Z2Z2)
          )
        );
        return res;
      }
      neg(p) {
        return [p[0], this.F.neg(p[1]), p[2]];
      }
      sub(a, b) {
        return this.add(a, this.neg(b));
      }
      double(p) {
        const F = this.F;
        const res = new Array(3);
        if (this.isZero(p)) return p;
        const A = F.square(p[0]);
        const B = F.square(p[1]);
        const C = F.square(B);
        let D = F.sub(
          F.square(F.add(p[0], B)),
          F.add(A, C)
        );
        D = F.add(D, D);
        const E = F.add(F.add(A, A), A);
        const FF = F.square(E);
        res[0] = F.sub(FF, F.add(D, D));
        let eightC = F.add(C, C);
        eightC = F.add(eightC, eightC);
        eightC = F.add(eightC, eightC);
        res[1] = F.sub(
          F.mul(
            E,
            F.sub(D, res[0])
          ),
          eightC
        );
        const Y1Z1 = F.mul(p[1], p[2]);
        res[2] = F.add(Y1Z1, Y1Z1);
        return res;
      }
      mulScalar(base, e) {
        return fUtils.mulScalar(this, base, e);
      }
      affine(p) {
        const F = this.F;
        if (this.isZero(p)) {
          return this.zero;
        } else {
          const Z_inv = F.inverse(p[2]);
          const Z2_inv = F.square(Z_inv);
          const Z3_inv = F.mul(Z2_inv, Z_inv);
          const res = new Array(3);
          res[0] = F.affine(F.mul(p[0], Z2_inv));
          res[1] = F.affine(F.mul(p[1], Z3_inv));
          res[2] = F.one;
          return res;
        }
      }
      equals(p1, p2) {
        const F = this.F;
        if (this.isZero(p1)) return this.isZero(p2);
        if (this.isZero(p2)) return this.isZero(p1);
        const Z1Z1 = F.square(p1[2]);
        const Z2Z2 = F.square(p2[2]);
        const U1 = F.mul(p1[0], Z2Z2);
        const U2 = F.mul(p2[0], Z1Z1);
        const Z1_cubed = F.mul(p1[2], Z1Z1);
        const Z2_cubed = F.mul(p2[2], Z2Z2);
        const S1 = F.mul(p1[1], Z2_cubed);
        const S2 = F.mul(p2[1], Z1_cubed);
        return F.equals(U1, U2) && F.equals(S1, S2);
      }
      toString(p) {
        const cp = this.affine(p);
        return `[ ${this.F.toString(cp[0])} , ${this.F.toString(cp[1])} ]`;
      }
    };
    module2.exports = GCurve;
  }
});

// bn128.js
var require_bn128 = __commonJS({
  "bn128.js"(exports2, module2) {
    var bigInt = require_bigint();
    var F1Field = require_zqfield();
    var F2Field = require_f2field();
    var F3Field = require_f3field();
    var GCurve = require_gcurve();
    var BN1282 = class {
      constructor() {
        this.q = bigInt("21888242871839275222246405745257275088696311157297823662689037894645226208583");
        this.r = bigInt("21888242871839275222246405745257275088548364400416034343698204186575808495617");
        this.g1 = [bigInt(1), bigInt(2), bigInt(1)];
        this.g2 = [
          [
            bigInt("10857046999023057135944570762232829481370756359578518086990519993285655852781"),
            bigInt("11559732032986387107991004021392285783925812861821192530917403151452391805634")
          ],
          [
            bigInt("8495653923123431417604973247489272438418190587263600148770280649306958101930"),
            bigInt("4082367875863433681332203403145435568316851327593401208105741076214120093531")
          ],
          [
            bigInt("1"),
            bigInt("0")
          ]
        ];
        this.nonResidueF2 = bigInt("21888242871839275222246405745257275088696311157297823662689037894645226208582");
        this.nonResidueF6 = [bigInt("9"), bigInt("1")];
        this.F1 = new F1Field(this.q);
        this.F2 = new F2Field(this.F1, this.nonResidueF2);
        this.G1 = new GCurve(this.F1, this.g1);
        this.G2 = new GCurve(this.F2, this.g2);
        this.F6 = new F3Field(this.F2, this.nonResidueF6);
        this.F12 = new F2Field(this.F6, this.nonResidueF6);
        this.Fr = new F1Field(this.r);
        const self = this;
        this.F12._mulByNonResidue = function(a) {
          return [self.F2.mul(this.nonResidue, a[2]), a[0], a[1]];
        };
        this._preparePairing();
      }
      _preparePairing() {
        this.loopCount = bigInt("29793968203157093288");
        if (this.loopCount.isNegative()) {
          this.loopCount = this.loopCount.neg();
          this.loopCountNeg = true;
        } else {
          this.loopCountNeg = false;
        }
        let lc = this.loopCount;
        this.loop_count_bits = [];
        while (!lc.isZero()) {
          this.loop_count_bits.push(lc.isOdd());
          lc = lc.shr(1);
        }
        this.two_inv = this.F1.inverse(bigInt(2));
        this.coef_b = bigInt(3);
        this.twist = [bigInt(9), bigInt(1)];
        this.twist_coeff_b = this.F2.mulScalar(this.F2.inverse(this.twist), this.coef_b);
        this.frobenius_coeffs_c1_1 = bigInt("21888242871839275222246405745257275088696311157297823662689037894645226208582");
        this.twist_mul_by_q_X = [
          bigInt("21575463638280843010398324269430826099269044274347216827212613867836435027261"),
          bigInt("10307601595873709700152284273816112264069230130616436755625194854815875713954")
        ];
        this.twist_mul_by_q_Y = [
          bigInt("2821565182194536844548159561693502659359617185244120367078079554186484126554"),
          bigInt("3505843767911556378687030309984248845540243509899259641013678093033130930403")
        ];
        this.final_exponent = bigInt("552484233613224096312617126783173147097382103762957654188882734314196910839907541213974502761540629817009608548654680343627701153829446747810907373256841551006201639677726139946029199968412598804882391702273019083653272047566316584365559776493027495458238373902875937659943504873220554161550525926302303331747463515644711876653177129578303191095900909191624817826566688241804408081892785725967931714097716709526092261278071952560171111444072049229123565057483750161460024353346284167282452756217662335528813519139808291170539072125381230815729071544861602750936964829313608137325426383735122175229541155376346436093930287402089517426973178917569713384748081827255472576937471496195752727188261435633271238710131736096299798168852925540549342330775279877006784354801422249722573783561685179618816480037695005515426162362431072245638324744480");
      }
      pairing(p1, p2) {
        const pre1 = this.precomputeG1(p1);
        const pre2 = this.precomputeG2(p2);
        const r1 = this.millerLoop(pre1, pre2);
        const res = this.finalExponentiation(r1);
        return res;
      }
      precomputeG1(p) {
        const Pcopy = this.G1.affine(p);
        const res = {};
        res.PX = Pcopy[0];
        res.PY = Pcopy[1];
        return res;
      }
      precomputeG2(p) {
        const Qcopy = this.G2.affine(p);
        const res = {
          QX: Qcopy[0],
          QY: Qcopy[1],
          coeffs: []
        };
        const R = {
          X: Qcopy[0],
          Y: Qcopy[1],
          Z: this.F2.one
        };
        let c;
        for (let i = this.loop_count_bits.length - 2; i >= 0; --i) {
          const bit = this.loop_count_bits[i];
          c = this._doubleStep(R);
          res.coeffs.push(c);
          if (bit) {
            c = this._addStep(Qcopy, R);
            res.coeffs.push(c);
          }
        }
        const Q1 = this.G2.affine(this._g2MulByQ(Qcopy));
        if (!this.F2.equals(Q1[2], this.F2.one)) {
          throw new Error("Expected values are not equal");
        }
        const Q2 = this.G2.affine(this._g2MulByQ(Q1));
        if (!this.F2.equals(Q2[2], this.F2.one)) {
          throw new Error("Expected values are not equal");
        }
        if (this.loopCountNeg) {
          R.Y = this.F2.neg(R.Y);
        }
        Q2[1] = this.F2.neg(Q2[1]);
        c = this._addStep(Q1, R);
        res.coeffs.push(c);
        c = this._addStep(Q2, R);
        res.coeffs.push(c);
        return res;
      }
      millerLoop(pre1, pre2) {
        let f = this.F12.one;
        let idx = 0;
        let c;
        for (let i = this.loop_count_bits.length - 2; i >= 0; --i) {
          const bit = this.loop_count_bits[i];
          c = pre2.coeffs[idx++];
          f = this.F12.square(f);
          f = this._mul_by_024(
            f,
            c.ell_0,
            this.F2.mulScalar(c.ell_VW, pre1.PY),
            this.F2.mulScalar(c.ell_VV, pre1.PX)
          );
          if (bit) {
            c = pre2.coeffs[idx++];
            f = this._mul_by_024(
              f,
              c.ell_0,
              this.F2.mulScalar(c.ell_VW, pre1.PY),
              this.F2.mulScalar(c.ell_VV, pre1.PX)
            );
          }
        }
        if (this.loopCountNeg) {
          f = this.F12.inverse(f);
        }
        c = pre2.coeffs[idx++];
        f = this._mul_by_024(
          f,
          c.ell_0,
          this.F2.mulScalar(c.ell_VW, pre1.PY),
          this.F2.mulScalar(c.ell_VV, pre1.PX)
        );
        c = pre2.coeffs[idx++];
        f = this._mul_by_024(
          f,
          c.ell_0,
          this.F2.mulScalar(c.ell_VW, pre1.PY),
          this.F2.mulScalar(c.ell_VV, pre1.PX)
        );
        return f;
      }
      finalExponentiation(elt) {
        const res = this.F12.exp(elt, this.final_exponent);
        return res;
      }
      _doubleStep(current) {
        const X = current.X;
        const Y = current.Y;
        const Z = current.Z;
        const A = this.F2.mulScalar(this.F2.mul(X, Y), this.two_inv);
        const B = this.F2.square(Y);
        const C = this.F2.square(Z);
        const D = this.F2.add(C, this.F2.add(C, C));
        const E = this.F2.mul(this.twist_coeff_b, D);
        const F = this.F2.add(E, this.F2.add(E, E));
        const G = this.F2.mulScalar(
          this.F2.add(B, F),
          this.two_inv
        );
        const H = this.F2.sub(
          this.F2.square(this.F2.add(Y, Z)),
          this.F2.add(B, C)
        );
        const I = this.F2.sub(E, B);
        const J = this.F2.square(X);
        const E_squared = this.F2.square(E);
        current.X = this.F2.mul(A, this.F2.sub(B, F));
        current.Y = this.F2.sub(
          this.F2.sub(this.F2.square(G), E_squared),
          this.F2.add(E_squared, E_squared)
        );
        current.Z = this.F2.mul(B, H);
        const c = {
          ell_0: this.F2.mul(I, this.twist),
          // ell_0 = xi * I
          ell_VW: this.F2.neg(H),
          // ell_VW = - H (later: * yP)
          ell_VV: this.F2.add(J, this.F2.add(J, J))
          // ell_VV = 3*J (later: * xP)
        };
        return c;
      }
      _addStep(base, current) {
        const X1 = current.X;
        const Y1 = current.Y;
        const Z1 = current.Z;
        const x2 = base[0];
        const y2 = base[1];
        const D = this.F2.sub(X1, this.F2.mul(x2, Z1));
        const E = this.F2.sub(Y1, this.F2.mul(y2, Z1));
        const F = this.F2.square(D);
        const G = this.F2.square(E);
        const H = this.F2.mul(D, F);
        const I = this.F2.mul(X1, F);
        const J = this.F2.sub(
          this.F2.add(H, this.F2.mul(Z1, G)),
          this.F2.add(I, I)
        );
        current.X = this.F2.mul(D, J);
        current.Y = this.F2.sub(
          this.F2.mul(E, this.F2.sub(I, J)),
          this.F2.mul(H, Y1)
        );
        current.Z = this.F2.mul(Z1, H);
        const c = {
          ell_0: this.F2.mul(
            this.twist,
            this.F2.sub(
              this.F2.mul(E, x2),
              this.F2.mul(D, y2)
            )
          ),
          // ell_0 = xi * (E * X2 - D * Y2)
          ell_VV: this.F2.neg(E),
          // ell_VV = - E (later: * xP)
          ell_VW: D
          // ell_VW = D (later: * yP )
        };
        return c;
      }
      _mul_by_024(a, ell_0, ell_VW, ell_VV) {
        let z0 = a[0][0];
        let z1 = a[0][1];
        let z2 = a[0][2];
        let z3 = a[1][0];
        let z4 = a[1][1];
        let z5 = a[1][2];
        const x0 = ell_0;
        const x2 = ell_VV;
        const x4 = ell_VW;
        const D0 = this.F2.mul(z0, x0);
        const D2 = this.F2.mul(z2, x2);
        const D4 = this.F2.mul(z4, x4);
        const t2 = this.F2.add(z0, z4);
        let t1 = this.F2.add(z0, z2);
        const s0 = this.F2.add(this.F2.add(z1, z3), z5);
        let S1 = this.F2.mul(z1, x2);
        let T3 = this.F2.add(S1, D4);
        let T4 = this.F2.add(this.F2.mul(this.nonResidueF6, T3), D0);
        z0 = T4;
        T3 = this.F2.mul(z5, x4);
        S1 = this.F2.add(S1, T3);
        T3 = this.F2.add(T3, D2);
        T4 = this.F2.mul(this.nonResidueF6, T3);
        T3 = this.F2.mul(z1, x0);
        S1 = this.F2.add(S1, T3);
        T4 = this.F2.add(T4, T3);
        z1 = T4;
        let t0 = this.F2.add(x0, x2);
        T3 = this.F2.sub(
          this.F2.mul(t1, t0),
          this.F2.add(D0, D2)
        );
        T4 = this.F2.mul(z3, x4);
        S1 = this.F2.add(S1, T4);
        t0 = this.F2.add(z2, z4);
        z2 = this.F2.add(T3, T4);
        t1 = this.F2.add(x2, x4);
        T3 = this.F2.sub(
          this.F2.mul(t0, t1),
          this.F2.add(D2, D4)
        );
        T4 = this.F2.mul(this.nonResidueF6, T3);
        T3 = this.F2.mul(z3, x0);
        S1 = this.F2.add(S1, T3);
        T4 = this.F2.add(T4, T3);
        z3 = T4;
        T3 = this.F2.mul(z5, x2);
        S1 = this.F2.add(S1, T3);
        T4 = this.F2.mul(this.nonResidueF6, T3);
        t0 = this.F2.add(x0, x4);
        T3 = this.F2.sub(
          this.F2.mul(t2, t0),
          this.F2.add(D0, D4)
        );
        T4 = this.F2.add(T4, T3);
        z4 = T4;
        t0 = this.F2.add(this.F2.add(x0, x2), x4);
        T3 = this.F2.sub(this.F2.mul(s0, t0), S1);
        z5 = T3;
        return [
          [z0, z1, z2],
          [z3, z4, z5]
        ];
      }
      _g2MulByQ(p) {
        const fmx = [p[0][0], this.F1.mul(p[0][1], this.frobenius_coeffs_c1_1)];
        const fmy = [p[1][0], this.F1.mul(p[1][1], this.frobenius_coeffs_c1_1)];
        const fmz = [p[2][0], this.F1.mul(p[2][1], this.frobenius_coeffs_c1_1)];
        return [
          this.F2.mul(this.twist_mul_by_q_X, fmx),
          this.F2.mul(this.twist_mul_by_q_Y, fmy),
          fmz
        ];
      }
    };
    module2.exports = BN1282;
  }
});

function unstringifyBigInts2(o) {
  let bigInt = require_bigint();
  if ((typeof(o) == "string") && (/^[0-9]+$/.test(o) ))  {
    return bigInt(o);
  } else if (Array.isArray(o)) {
    return o.map(unstringifyBigInts2);
  } else if (typeof o == "object") {
    const res = {};
    for (let k in o) {
      res[k] = unstringifyBigInts2(o[k]);
    }
    return res;
  } else {
    return o;
  }
}

const fs = require('fs');
const path = require('path');
let verification_key = JSON.parse(fs.readFileSync(path.resolve(__dirname, '..', 'tornado', 'verification_key.json')));

// verifier_groth.js
var BN128 = require_bn128();
var bn128 = new BN128();
var G1 = bn128.G1;
function verify(proof) {
  verification_key = unstringifyBigInts2(verification_key);
  proof = unstringifyBigInts2(proof);
  let cpub = verification_key.IC[0];
  for (let s = 0; s < verification_key.nPublic; s++) {
    cpub = G1.add(cpub, G1.mulScalar(verification_key.IC[s + 1], proof.publicSignals[s]));
  }
  let left = bn128.pairing(proof.pi_a, proof.pi_b);
  let a = bn128.pairing(cpub, verification_key.vk_gamma_2);
  let b = bn128.pairing(proof.pi_c, verification_key.vk_delta_2)
  let mul_l = verification_key.vk_alfabeta_12;
  let mul_r = bn128.F12.mul(a, b)
  let right = bn128.F12.mul(mul_l, mul_r);
  return bn128.F12.equals(left, right);
}

module.exports = { verify }

if (require.main === module) {
  const input_obj = JSON.parse(process.argv[2]);
  if (verify(input_obj)) {
    return 0;
  }
  return 1;
}
