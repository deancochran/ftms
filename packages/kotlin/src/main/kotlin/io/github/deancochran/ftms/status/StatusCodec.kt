package io.github.deancochran.ftms.status

/** Raw operand of a parameterized Machine Status. requestOpcode is its mapped Control Point opcode. */
public class MachineStatusParameter(public val requestOpcode: Int, operands: IntArray) {
    private val rawOperands = operands.copyOf()
    public val operands: IntArray get() = rawOperands.copyOf()
    public fun operandAt(index: Int): Int = rawOperands[index]
}
public class MachineStatus @JvmOverloads constructor(
    public val opcode: Int, public val action: Int = 0, public val parameter: MachineStatusParameter? = null,
    public val unknownOpcode: Boolean = false, public val reservedValue: Boolean = false,
    public val truncated: Boolean = false, public val trailingBytes: Boolean = false,
)
public class TrainingStatus @JvmOverloads constructor(
    public val flags: Int, public val code: Int, text: ByteArray = ByteArray(0), public val textOffset: Int = 0,
    public val textPresent: Boolean = false, public val extendedString: Boolean = false, public val reservedFlags: Int = 0,
    public val reservedValue: Boolean = false, public val invalidFlags: Boolean = false, public val invalidUtf8: Boolean = false,
    public val truncated: Boolean = false, public val trailingBytes: Boolean = false,
) { private val rawText=text.copyOf(); public val text: ByteArray get()=rawText.copyOf(); public val textSize: Int get()=rawText.size }

/** Stateless raw FTMS Training Status and Machine Status codecs. */
public object StatusCodec {
    private fun u16(b: ByteArray, i: Int)= (b[i].toInt() and 255) or ((b[i+1].toInt() and 255) shl 8)
    private fun i16(b: ByteArray,i:Int): Int { val v=u16(b,i); return if(v>32767) v-65536 else v }
    private fun le(v:Int)=byteArrayOf((v and 255).toByte(),((v ushr 8) and 255).toByte())
    private fun length(code:Int):Int = when(code) {1,3,4,255->1; 2,9,20->2; 13->4;15->5;16,18->7;17->11; in 5..8, in 10..12,14,19,21->3; else->0}
    private fun mapped(code:Int):Int = when { code in 5..9 -> code-3; code in 10..19 || code==21 -> code-1; else -> -1 }
    private fun validUtf8(bytes:ByteArray):Boolean = try { java.nio.charset.StandardCharsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT).onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(bytes)); true } catch (_: java.nio.charset.CharacterCodingException) { false }

    @JvmStatic public fun decodeMachine(bytes: ByteArray): MachineStatus {
        if(bytes.isEmpty()) return MachineStatus(0,unknownOpcode=true,truncated=true); val code=bytes[0].toInt() and 255; val n=length(code)
        if(n==0) return MachineStatus(code,unknownOpcode=true); if(bytes.size<n) return MachineStatus(code,truncated=true)
        val action=if(code==2 || code==20) bytes[1].toInt() and 255 else 0; val reserved=(code==2 && action !in 1..2)||(code==20 && action !in 1..4)
        val operands=when(code) {5->intArrayOf(u16(bytes,1));6,7,8->intArrayOf(i16(bytes,1));9->intArrayOf(bytes[1].toInt()and 255);10,11,12,14,19,21->intArrayOf(u16(bytes,1));13->intArrayOf((bytes[1].toInt()and 255)or((bytes[2].toInt()and 255)shl 8)or((bytes[3].toInt()and 255)shl 16));15,16,17->IntArray((n-1)/2){u16(bytes,1+it*2)};18->intArrayOf(i16(bytes,1),i16(bytes,3),bytes[5].toInt()and 255,bytes[6].toInt()and 255); else->IntArray(0)}
        val parameter=if(mapped(code)>=0 && code!=20) MachineStatusParameter(mapped(code),operands) else null
        return MachineStatus(code,action,parameter,false,reserved,false,bytes.size>n)
    }
    @JvmStatic public fun encodeMachine(status: MachineStatus): ByteArray {
        require(status.opcode == 2 || status.opcode == 20 || status.action == 0) {
            "action supplied for a machine status without an action field"
        }
        val n=length(status.opcode); require(n!=0&&!status.unknownOpcode&&!status.reservedValue&&!status.truncated&&!status.trailingBytes) { "non-canonical machine status" }; require(!(status.opcode==2 && status.action !in 1..2) && !(status.opcode==20 && status.action !in 1..4)) { "reserved action" }
        val expected=mapped(status.opcode); require(if(expected>=0) status.parameter?.requestOpcode==expected else status.parameter==null) { "machine status parameter mismatch" }
        status.parameter?.let { parameter ->
            val operands = parameter.operands
            val count = when (status.opcode) { 15 -> 2; 16 -> 3; 17 -> 5; 18 -> 4; else -> 1 }
            require(operands.size == count) { "machine status operand count mismatch" }
            operands.forEachIndexed { index, value ->
                val range = when {
                    status.opcode in 6..8 || (status.opcode == 18 && index < 2) -> -32768..32767
                    status.opcode == 9 || (status.opcode == 18 && index >= 2) -> 0..255
                    status.opcode == 13 -> 0..0xffffff
                    else -> 0..65535
                }
                require(value in range) { "machine status operand outside wire range" }
            }
        }
        val out=ByteArray(n); out[0]=status.opcode.toByte()
        if(status.opcode==2||status.opcode==20) out[1]=status.action.toByte() else status.parameter?.let { p -> val a=p.operands; fun w(i:Int,v:Int){val x=le(v);out[i]=x[0];out[i+1]=x[1]}; when(status.opcode) {5,9-> { if(status.opcode==5) w(1,a[0]) else out[1]=a[0].toByte() };6,7,8,10,11,12,14,19,21->w(1,a[0]);13->{require(a[0] in 0..0xffffff);out[1]=a[0].toByte();out[2]=(a[0] ushr 8).toByte();out[3]=(a[0] ushr 16).toByte()};15,16,17->a.forEachIndexed{i,v->w(1+i*2,v)};18->{w(1,a[0]);w(3,a[1]);out[5]=a[2].toByte();out[6]=a[3].toByte()} } }
        return out
    }
    @JvmStatic public fun decodeTraining(bytes: ByteArray): TrainingStatus {
        if(bytes.size<2) return TrainingStatus(if(bytes.isEmpty())0 else bytes[0].toInt()and 255,0,truncated=true)
        val flags=bytes[0].toInt()and 255; val code=bytes[1].toInt()and 255; val has=flags and 1 !=0; val text=if(has)bytes.copyOfRange(2,bytes.size) else ByteArray(0)
        return TrainingStatus(flags,code,text,if(has)2 else 0,has,flags and 2 !=0,flags and 0xfc,code>15,(flags and 2 !=0&&!has),has&&!validUtf8(text),false,!has&&bytes.size>2)
    }
    @JvmStatic @JvmOverloads public fun encodeTraining(status: TrainingStatus, text: String = ""): ByteArray {
        require(status.flags in 0..255) { "training status flags outside wire range" }
        require(status.code in 0..15 && status.flags and 0xfc == 0 && !(status.flags and 2 != 0 && status.flags and 1 == 0)) { "invalid training status flags or code" }; require(!status.truncated&&status.reservedFlags==0&&!status.reservedValue&&!status.invalidFlags&&!status.invalidUtf8&&!status.trailingBytes) { "diagnostic training status cannot encode" }
        val encoded = try {
            Charsets.UTF_8.newEncoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
                .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT).encode(java.nio.CharBuffer.wrap(text))
        } catch (error: java.nio.charset.CharacterCodingException) {
            throw IllegalArgumentException("invalid UTF-16 text", error)
        }
        val raw = ByteArray(encoded.remaining()).also { encoded.get(it) }
        require(status.flags and 1 != 0 || raw.isEmpty()) { "text supplied without text-present flag" }
        return byteArrayOf(status.flags.toByte(),status.code.toByte()) + if(status.flags and 1 != 0) raw else ByteArray(0)
    }
}
