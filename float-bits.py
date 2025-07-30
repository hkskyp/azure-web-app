import streamlit as st
import struct
import math

# --- 상수 정의 ---
# IEEE 754 각 정밀도에 대한 설정값
IEEE754_CONFIG = {
    'float': {'format': 'f', 'unpack': 'I', 'bits': 32, 'exp_bits': 8, 'mantissa_bits': 23, 'bias': 127},
    'double': {'format': 'd', 'unpack': 'Q', 'bits': 64, 'exp_bits': 11, 'mantissa_bits': 52, 'bias': 1023}
}

# UI에 사용될 색상
COLORS = {'sign': '#D32F2F', 'exp': '#1976D2', 'mantissa': '#7B1FA2', 'bg': '#F5F5F5', 'dot': '#424242'}


# --- 핵심 변환 함수 ---

def to_bits(value, precision='double'):
    """실수를 IEEE 754 비트 문자열로 변환합니다."""
    config = IEEE754_CONFIG[precision]
    # 'nan'과 'inf'는 struct로 직접 패킹
    if math.isnan(value):
        return format(struct.unpack(config['unpack'], struct.pack(config['format'], float('nan')))[0], f'0{config["bits"]}b')
    if math.isinf(value):
        return format(struct.unpack(config['unpack'], struct.pack(config['format'], value))[0], f'0{config["bits"]}b')
    
    packed = struct.pack(config['format'], value)
    unpacked = struct.unpack(config['unpack'], packed)[0]
    return format(unpacked, f'0{config["bits"]}b')

def parse_bits(bits, precision='double'):
    """비트 문자열을 부호, 지수, 가수로 분리합니다."""
    config = IEEE754_CONFIG[precision]
    return bits[0], bits[1:1+config['exp_bits']], bits[1+config['exp_bits']:]

def decimal_to_binary(value, max_bits=20):
    """십진 실수를 일반적인 2진수 문자열로 변환합니다."""
    if value == 0: return "0.0", "0", "0", False
    
    sign, value = ("-" if value < 0 else "", abs(value))
    integer_part, fraction_part = int(value), value - int(value)
    
    int_binary = bin(integer_part)[2:] if integer_part else "0"
    frac_binary, original_frac = "", fraction_part
    
    for _ in range(max_bits):
        if fraction_part == 0: break
        fraction_part *= 2
        frac_binary += "1" if fraction_part >= 1 else "0"
        if fraction_part >= 1: fraction_part -= 1
    
    is_infinite = original_frac != 0 and fraction_part != 0
    return f"{sign}{int_binary}.{frac_binary or '0'}", int_binary, frac_binary or "0", is_infinite

def calculate_ieee754(sign, exponent, mantissa, precision):
    """
    IEEE 754 비트로부터 실제 값을 계산합니다.
    정규화, 비정규화, 0, 무한대, NaN을 모두 처리합니다.
    """
    config = IEEE754_CONFIG[precision]
    sign_val = int(sign)
    exp_val = int(exponent, 2)
    mantissa_val = sum(int(b) * (2 ** -(i + 1)) for i, b in enumerate(mantissa))
    
    max_exp = (2**config['exp_bits']) - 1

    # 특수 값 판별
    if exp_val == 0:
        if mantissa_val == 0:
            # Case: 0 (영)
            number_type = "Zero"
            actual_exp = 1 - config['bias'] # 기술적으로는 사용되지 않음
            result = (-1)**sign_val * 0.0
        else:
            # Case: Denormalized (비정규화된 수)
            number_type = "Denormalized"
            actual_exp = 1 - config['bias']
            # 공식: (-1)^S * (0 + M) * 2^(1 - bias)
            result = ((-1)**sign_val) * mantissa_val * (2**actual_exp)
    elif exp_val == max_exp:
        if mantissa_val == 0:
            # Case: Infinity (무한대)
            number_type = "Infinity"
            actual_exp = None
            result = float('-inf') if sign_val == 1 else float('inf')
        else:
            # Case: NaN (Not a Number)
            number_type = "NaN (Not a Number)"
            actual_exp = None
            result = float('nan')
    else:
        # Case: Normalized (정규화된 수)
        number_type = "Normalized"
        actual_exp = exp_val - config['bias']
        # 공식: (-1)^S * (1 + M) * 2^(E - bias)
        result = ((-1)**sign_val) * (1 + mantissa_val) * (2**actual_exp)
        
    return sign_val, exp_val, actual_exp, mantissa_val, result, number_type


# --- UI 렌더링 함수 ---

def render_colored_html(sign, exp, mantissa, is_infinite=False):
    """색상이 적용된 HTML을 생성합니다."""
    return f"""
    <div style="font-family: 'Courier New', monospace; font-size: 24px; margin: 15px 0; font-weight: bold;">
        <span style="color: {COLORS['sign']};">{'-' if sign and sign != '0' else ''}</span>
        <span style="color: {COLORS['exp']};">{exp}</span>
        <span style="color: {COLORS['dot']};">.</span>
        <span style="color: {COLORS['mantissa']};">{mantissa}{'...' if is_infinite else ''}</span>
    </div>
    """

def render_ieee_bits(sign, exp, mantissa):
    """IEEE 754 비트를 시각적으로 표시합니다."""
    return f"""
    <div style="font-family: 'Courier New', monospace; font-size: 20px; margin: 10px 0; font-weight: bold;">
        <span style="color: {COLORS['sign']}; background-color: {COLORS['bg']}; padding: 4px; border: 2px solid {COLORS['sign']}; margin-right: 2px;">{sign}</span>
        <span style="color: {COLORS['exp']}; background-color: {COLORS['bg']}; padding: 4px; border: 2px solid {COLORS['exp']}; margin-right: 2px;">{exp}</span>
        <span style="color: {COLORS['mantissa']}; background-color: {COLORS['bg']}; padding: 4px; border: 2px solid {COLORS['mantissa']};">{mantissa}</span>
    </div>
    """

# --- 화면 구성 함수 ---

def display_binary_representation(value):
    """일반 2진수 표현을 화면에 표시합니다."""
    st.markdown("### 🔢 Standard Binary Representation")
    if value == 0:
        st.markdown("**Binary:** `0.0`")
        return
    
    _, int_part, frac_part, is_infinite = decimal_to_binary(value)
    st.markdown("**Binary Representation:**")
    st.markdown(render_colored_html(("-" if value < 0 else ""), int_part, frac_part, is_infinite), unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    abs_val = abs(value)
    
    with col1:
        st.markdown("🔵 **Integer Part**")
        st.write(f"Decimal: {int(abs_val)}")
        st.write(f"Binary: {int_part}")
    
    with col2:
        st.markdown("🟣 **Fractional Part**")
        st.write(f"Decimal: {abs_val - int(abs_val):.10f}")
        st.write(f"Binary: 0.{frac_part}{'...' if is_infinite else ''}")
    
    with st.expander("💡 Differences from IEEE 754 Representation"):
        st.write("**Standard Binary**: Fixed-point, intuitive, infinite decimals possible")
        st.write("**IEEE 754**: Floating-point, wide range, limited precision")

def display_ieee754_analysis(value, precision, title):
    """IEEE 754 분석 결과를 화면에 표시합니다."""
    st.markdown(f"### {title}")
    
    bits = to_bits(value, precision)
    sign, exp, mantissa = parse_bits(bits, precision)
    
    st.markdown(f"**{title} Bit Representation:**")
    st.markdown(render_ieee_bits(sign, exp, mantissa), unsafe_allow_html=True)
    st.code(f"Complete bits: {bits}")
    
    # 각 부분 분석
    calc_result = calculate_ieee754(sign, exp, mantissa, precision)
    sign_val, exp_val, actual_exp, mantissa_val, result, number_type = calc_result
    
    st.info(f"**Identified Type:** **{number_type}**")
    
    col1, col2, col3 = st.columns(3)
    bias = IEEE754_CONFIG[precision]['bias']
    
    with col1:
        st.markdown("🔴 **Sign**")
        st.write(f"Value: {sign} → {'Negative' if sign == '1' else 'Positive'}")
        st.latex(f"(-1)^{{{sign}}} = {(-1)**sign_val}")
    
    with col2:
        st.markdown("🔵 **Exponent**")
        st.write(f"Value: {exp} (Decimal: {exp_val})")
        if number_type == "Normalized":
            st.write(f"Actual exponent: {exp_val} - {bias} = {actual_exp}")
            st.latex(f"2^{{{actual_exp}}}")
        elif number_type == "Denormalized":
            st.write(f"Actual exponent: 1 - {bias} = {actual_exp}")
            st.warning("Exponent is 0, so this is a denormalized number.")
        elif number_type in ["Infinity", "NaN (Not a Number)"]:
            st.warning("All exponent bits are 1, so this is a special value.")
        else: # Zero
            st.write("Represents 0.")

    with col3:
        st.markdown("🟣 **Mantissa**")
        st.write(f"Value (M): {mantissa_val:.20f}")
        if number_type == "Normalized":
            st.latex(f"1 + M = 1 + {mantissa_val:.10f}")
            st.info("Normalized numbers have an implicit 1 added.")
        elif number_type == "Denormalized":
            st.latex(f"0 + M = {mantissa_val:.10f}")
            st.info("Denormalized numbers have an implicit 0 added.")
        else: # Zero, Inf, NaN
            st.write(f"Mantissa value: {mantissa_val:.10f}")

    # 수식 표현
    st.markdown("#### 📐 IEEE 754 Formula")
    if number_type == "Normalized":
        st.latex(f"\\text{{Value}} = (-1)^S \\times (1 + M) \\times 2^{{E - \\text{{bias}}}}")
        st.write(f"**Calculation:** `(-1)^{sign_val} × (1 + {mantissa_val}) × 2^({exp_val} - {bias})`")
    elif number_type == "Denormalized":
        st.latex(f"\\text{{Value}} = (-1)^S \\times (0 + M) \\times 2^{{1 - \\text{{bias}}}}")
        st.write(f"**Calculation:** `(-1)^{sign_val} × ({mantissa_val}) × 2^({1} - {bias})`")
    elif number_type == "Zero":
        st.latex(f"\\text{{Value}} = (-1)^S \\times 0")
    elif number_type == "Infinity":
        st.latex(f"\\text{{Value}} = (-1)^S \\times \\infty")
    else: # NaN
        st.write("**Not a Number**")

    if result is not None:
        st.success(f"**Calculated Result:** `{result}`")
        
        # 실제 저장값과 비교
        stored = struct.unpack(IEEE754_CONFIG[precision]['format'], 
                               struct.pack(IEEE754_CONFIG[precision]['format'], value))[0]
        st.info(f"**Actual Stored Value:** `{stored}`")


def main():
    st.set_page_config(page_title="IEEE 754 Float Bit Viewer", layout="wide")
    st.title("🔢 IEEE 754 Floating Point Bit Representation Analyzer")
    st.markdown("Enter a real number to see the bit representation in 32-bit Float and 64-bit Double formats.")
    
    # 사이드바
    with st.sidebar:
        st.markdown("### 📚 IEEE 754 Standard")
        for name, config in IEEE754_CONFIG.items():
            precision_name = "Single" if name == 'float' else "Double"
            st.write(f"**{config['bits']}-bit {precision_name}:** 1 (Sign) + {config['exp_bits']} (Exponent) + {config['mantissa_bits']} (Mantissa) bits")
        
        st.markdown("### 🎨 Color Coding")
        st.markdown("🔴 Sign 🔵 Exponent 🟣 Mantissa")
    
    # 입력 섹션
    col1, col2 = st.columns([2, 1])
    with col1:
        user_input = st.text_input("Enter a real number:", value="3.14159")
    with col2:
        if st.button("π"): user_input = "3.14159"
        if st.button("e"): user_input = "2.71828"
    
    try:
        if user_input:
            # 'inf', 'nan' 등의 문자열 입력을 float으로 변환
            user_input_lower = user_input.lower()
            if 'inf' in user_input_lower:
                value = float('-inf') if user_input_lower.startswith('-') else float('inf')
            elif 'nan' in user_input_lower:
                value = float('nan')
            else:
                value = float(user_input)
                
            st.markdown(f"### Input Value: **{value}**")
            
            # 일반 2진수 표현 (NaN, Inf 제외)
            if not (math.isinf(value) or math.isnan(value)):
                display_binary_representation(value)
                st.markdown("---")
            
            # IEEE 754 분석
            display_ieee754_analysis(value, 'float', "32-bit Float (Single Precision)")
            st.markdown("---")
            display_ieee754_analysis(value, 'double', "64-bit Double (Double Precision)")
            
            # 비교 분석
            st.markdown("---")
            st.subheader("📊 Comparison Analysis")
            comparison_data = {
                "Category": ["Data Type", "Total Bits", "Sign", "Exponent", "Mantissa", "Bias"],
                "32-bit": ["Single", "32", "1", "8", "23", "127"],
                "64-bit": ["Double", "64", "1", "11", "52", "1023"]
            }
            st.table(comparison_data)
            
            # 정밀도 비교 (숫자인 경우에만)
            if not (math.isinf(value) or math.isnan(value)):
                st.markdown("### 🎯 Precision Difference")
                float_val = struct.unpack('f', struct.pack('f', value))[0]
                error = abs(value - float_val)
                
                st.write(f"**Original (processed as 64-bit Double):** `{value}`")
                st.write(f"**When stored as 32-bit Float:** `{float_val}`")
                st.write(f"**Error:** `{error:.2e}`")
                
                if error > 1e-9 and value != 0:
                    st.warning("⚠️ Precision loss may occur in 32-bit Float.")
    
    except ValueError:
        st.error("Please enter a valid real number or 'inf', 'nan'.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()