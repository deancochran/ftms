#nullable enable
using System;
using System.Collections.Generic;

namespace DeanCochran.Ftms
{
    /// <summary>Integer codes accepted by <see cref="CapabilitySnapshot.Discovery"/>.</summary>
    public enum CapabilityDiscoveryState { NotAttempted = 0, Partial = 1, Complete = 2, Failed = 3 }
    /// <summary>Integer codes accepted by <see cref="CapabilitySnapshot.Scope"/>.</summary>
    public enum CapabilityServiceScope { Unknown = 0, Present = 1, Absent = 2, Ambiguous = 3 }
    /// <summary>Integer codes accepted by <see cref="CapabilityCharacteristic.ReadState"/>.</summary>
    public enum CapabilityReadState { NotAttempted = 0, Success = 1, Failed = 2 }
    /// <summary>Integer codes accepted by <see cref="CapabilityCharacteristic.Reason"/>.</summary>
    public enum CapabilityReadReason { None = 0, Generic = 1, SecurityRequired = 2, Unavailable = 3, Timeout = 4, Disconnected = 5 }
    public enum CapabilityPresence { Unknown, Absent, Unique, Ambiguous }
    public enum CapabilityDecodeState { NotDecoded, Valid, Malformed, ReadFailed }
    public enum CapabilityDeclaration { Unknown, NotSupported, Supported }
    public enum CapabilityPrerequisites { NotApplicable, Satisfied, Incomplete, Inconsistent }
    public enum CapabilityCharacteristicKind
    {
        Unknown, Feature, Treadmill, CrossTrainer, StepClimber, StairClimber, Rower, IndoorBike,
        TrainingStatus, SpeedRange, InclinationRange, ResistanceRange, HeartRateRange, PowerRange,
        ControlPoint, MachineStatus
    }
    [Flags]
    public enum CapabilityReasons
    {
        None = 0, ServiceScope = 1, DiscoveryIncomplete = 2, FeatureUnavailable = 4,
        FeatureInvalid = 8, ControlPointUnavailable = 16, ControlPointInvalid = 32,
        MachineStatusUnavailable = 64, MachineStatusInvalid = 128, RangeUnavailable = 256,
        RangeInvalid = 512, InsufficientC7Evidence = 1024
    }
    [Flags]
    public enum CharacteristicProperties : ushort
    {
        None = 0, Broadcast = 1, Read = 2, WriteWithoutResponse = 4, Write = 8,
        Notify = 16, Indicate = 32, AuthenticatedSignedWrites = 64, ExtendedProperties = 128
    }

    /// <summary>Caller-owned FTMS evidence. Evaluation is static and never authorizes control.</summary>
    public sealed class CapabilityCharacteristic
    {
        private readonly byte[] _bytes;

        public CapabilityCharacteristic(string uuid, CharacteristicProperties properties, CapabilityReadState readState, CapabilityReadReason reason, byte[] bytes)
            : this(uuid, (ushort)properties, (int)readState, (int)reason, bytes) { }

        public CapabilityCharacteristic(string uuid, ushort properties, int readState, int reason, byte[] bytes)
        {
            Uuid = uuid ?? throw new ArgumentNullException(nameof(uuid));
            Properties = properties;
            ReadState = readState;
            Reason = reason;
            _bytes = (byte[])(bytes ?? throw new ArgumentNullException(nameof(bytes))).Clone();
        }

        public string Uuid { get; private set; }
        public ushort Properties { get; private set; }
        public int ReadState { get; private set; }
        public int Reason { get; private set; }
        /// <summary>Returns a defensive copy of the caller-provided raw read value.</summary>
        public byte[] Bytes { get { return (byte[])_bytes.Clone(); } }
    }

    public sealed class CapabilityC7
    {
        public CapabilityC7(bool? bondingSupported, bool? featureMayChangeOverLifetime)
        { BondingSupported = bondingSupported; FeatureMayChangeOverLifetime = featureMayChangeOverLifetime; }
        public bool? BondingSupported { get; private set; }
        public bool? FeatureMayChangeOverLifetime { get; private set; }
    }

    public sealed class CapabilitySnapshot
    {
        public CapabilitySnapshot(CapabilityDiscoveryState discovery, CapabilityServiceScope scope, uint generation, IList<CapabilityCharacteristic> characteristics, CapabilityC7? c7 = null)
            : this((int)discovery, (int)scope, generation, characteristics, c7) { }
        public CapabilitySnapshot(int discovery, int scope, uint generation, IList<CapabilityCharacteristic> characteristics, CapabilityC7? c7 = null)
        { Discovery = discovery; Scope = scope; Generation = generation; Characteristics = new List<CapabilityCharacteristic>(characteristics ?? throw new ArgumentNullException(nameof(characteristics))).AsReadOnly(); C7 = c7; }
        public int Discovery { get; private set; }
        public int Scope { get; private set; }
        public uint Generation { get; private set; }
        public IList<CapabilityCharacteristic> Characteristics { get; private set; }
        public CapabilityC7? C7 { get; private set; }
    }

    public sealed class CapabilityRangeValue
    {
        public CapabilityRangeValue(int kind, int minimum, int maximum, int increment, int scaleDivisor, int unit)
        { Kind = kind; Minimum = minimum; Maximum = maximum; Increment = increment; ScaleDivisor = scaleDivisor; Unit = unit; }
        public int Kind { get; private set; }
        public int Minimum { get; private set; }
        public int Maximum { get; private set; }
        public int Increment { get; private set; }
        public int ScaleDivisor { get; private set; }
        public int Unit { get; private set; }
    }
    public sealed class CapabilityRangeInspection
    {
        public CapabilityRangeInspection(int presence, int decode, int? inputIndex, CapabilityRangeValue? value)
        { Presence = presence; Decode = decode; InputIndex = inputIndex; Value = value; }
        public int Presence { get; private set; }
        public int Decode { get; private set; }
        public int? InputIndex { get; private set; }
        public CapabilityRangeValue? Value { get; private set; }
        public CapabilityPresence PresenceState => (CapabilityPresence)Presence;
        public CapabilityDecodeState DecodeState => (CapabilityDecodeState)Decode;
    }
    public sealed class CapabilityOperation
    {
        public CapabilityOperation(int opcode, int targetBit, int optionalInTable, int declaration, int prerequisite, int reasons)
        { Opcode = opcode; TargetBit = targetBit; OptionalInTable = optionalInTable; Declaration = declaration; Prerequisite = prerequisite; Reasons = reasons; }
        public int Opcode { get; private set; }
        public int TargetBit { get; private set; }
        public int OptionalInTable { get; private set; }
        public int Declaration { get; private set; }
        public int Prerequisite { get; private set; }
        public int Reasons { get; private set; }
        public CapabilityDeclaration DeclaredSupport => (CapabilityDeclaration)Declaration;
        /// <summary>Static evidence only; Satisfied is never permission to execute a control.</summary>
        public CapabilityPrerequisites StaticPrerequisites => (CapabilityPrerequisites)Prerequisite;
        public CapabilityReasons ReasonFlags => (CapabilityReasons)Reasons;
    }
    public sealed class CapabilityObservation
    {
        private readonly byte[] _rawBytes;

        public CapabilityObservation(int inputIndex, string uuid, int properties, int knownKind, int readState, int reason, byte[] rawBytes)
        {
            InputIndex = inputIndex;
            Uuid = uuid;
            Properties = properties;
            KnownKind = knownKind;
            ReadState = readState;
            Reason = reason;
            _rawBytes = (byte[])rawBytes.Clone();
            ReadSize = _rawBytes.Length;
        }
        public int InputIndex { get; private set; }
        public string Uuid { get; private set; }
        public int Properties { get; private set; }
        public int KnownKind { get; private set; }
        public int ReadState { get; private set; }
        public int Reason { get; private set; }
        public int ReadSize { get; private set; }
        /// <summary>Returns a defensive copy of the raw bytes from this stable observation.</summary>
        public byte[] RawBytes { get { return (byte[])_rawBytes.Clone(); } }
    }
    public sealed class CapabilityDiagnostic
    {
        public CapabilityDiagnostic(int code, int knownKind, int? inputIndex) { Code = code; KnownKind = knownKind; InputIndex = inputIndex; }
        public int Code { get; private set; }
        public int KnownKind { get; private set; }
        public int? InputIndex { get; private set; }
    }
    public sealed class CapabilityFeatureEvidence
    {
        public CapabilityPresence Presence { get; }
        public CapabilityDecodeState DecodeState { get; }
        public int? InputIndex { get; }
        public uint MachineRaw { get; }
        public uint TargetRaw { get; }
        public uint MachineUnknown { get; }
        public uint TargetUnknown { get; }
        internal CapabilityFeatureEvidence(long?[] values)
        {
            Presence = (CapabilityPresence)values[0]!.Value;
            DecodeState = (CapabilityDecodeState)values[1]!.Value;
            InputIndex = (int?)values[2];
            MachineRaw = (uint)values[3]!.Value;
            TargetRaw = (uint)values[4]!.Value;
            MachineUnknown = (uint)values[5]!.Value;
            TargetUnknown = (uint)values[6]!.Value;
        }
    }

    public sealed class CapabilityReport
    {
        internal CapabilityReport(CapabilitySnapshot s, int[] presence, long?[] feature, IList<CapabilityRangeInspection> ranges, IList<CapabilityOperation> operations, IList<CapabilityObservation> observations, IList<CapabilityDiagnostic> diagnostics)
        {
            Generation = s.Generation; Discovery = s.Discovery; Scope = s.Scope;
            ObservationCount = observations.Count; DiagnosticCount = diagnostics.Count;
            Presence = Array.AsReadOnly(presence);
            Feature = new CapabilityFeatureEvidence(feature);
            Ranges = new List<CapabilityRangeInspection>(ranges).AsReadOnly();
            Operations = new List<CapabilityOperation>(operations).AsReadOnly();
            Observations = new List<CapabilityObservation>(observations).AsReadOnly();
            Diagnostics = new List<CapabilityDiagnostic>(diagnostics).AsReadOnly();
        }
        public uint Generation { get; private set; }
        public int Discovery { get; private set; }
        public int Scope { get; private set; }
        public int ObservationCount { get; private set; }
        public int DiagnosticCount { get; private set; }
        public IList<int> Presence { get; private set; }
        public CapabilityFeatureEvidence Feature { get; private set; }
        public IList<CapabilityRangeInspection> Ranges { get; private set; }
        public IList<CapabilityOperation> Operations { get; private set; }
        public IList<CapabilityObservation> Observations { get; private set; }
        public IList<CapabilityDiagnostic> Diagnostics { get; private set; }
        public CapabilityPresence PresenceOf(CapabilityCharacteristicKind kind)
        {
            if ((uint)kind >= Presence.Count) throw new ArgumentOutOfRangeException(nameof(kind));
            return (CapabilityPresence)Presence[(int)kind];
        }
    }

    public static class CapabilityEvaluator
    {
        private const string Base = "00001000800000805f9b34fb";
        private static readonly int[] TargetForOpcode = { 255, 255, 0, 1, 2, 3, 4, 255, 255, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 };
        private static readonly int[] RangeForTarget = { 0, 1, 2, 4, 3 };
        private static readonly int[] RequiredProperties = { 0, 2, 16, 16, 16, 16, 16, 16, 18, 2, 2, 2, 2, 2, 40, 16 };

        public static CapabilityReport Evaluate(CapabilitySnapshot s)
        {
            return Evaluate(s, false);
        }
        /// <param name="s">Caller-supplied discovery and read evidence, not execution authority.</param>
        /// <param name="signedResistanceTenths">Caller-selected resistance wire interpretation; it is never inferred.</param>
        public static CapabilityReport Evaluate(CapabilitySnapshot s, bool signedResistanceTenths)
        {
            if (s == null || s.Discovery < 0 || s.Discovery > 3 || s.Scope < 0 || s.Scope > 3)
                throw new ArgumentOutOfRangeException(nameof(s));

            IList<CapabilityCharacteristic> cs = s.Characteristics;
            int n = cs.Count;
            int[] kinds = new int[n];
            for (int i = 0; i < n; i++)
            {
                Validate(cs[i]);
                kinds[i] = Kind(cs[i].Uuid);
            }

            bool scopeOk = s.Scope == 1;
            bool absent = s.Scope == 2 && s.Discovery == 2 && n == 0;
            int[] first = new int[16];
            int[] counts = new int[16];
            int[] presence = new int[16];
            for (int k = 0; k < 16; k++) first[k] = -1;
            var diagnostics = new List<CapabilityDiagnostic>();
            for (int i = 0; i < n; i++)
            {
                int k = kinds[i];
                if (k == 0) continue;
                if (first[k] < 0) first[k] = i;
                if (counts[k] < 2) counts[k]++;
            }
            for (int k = 1; k < 16; k++)
            {
                if (counts[k] > 1) { presence[k] = 3; diagnostics.Add(new CapabilityDiagnostic(3, k, first[k])); }
                else if (counts[k] == 1) presence[k] = 2;
                else if (s.Discovery == 2 && scopeOk) presence[k] = 1;
            }
            if (!scopeOk) diagnostics.Add(new CapabilityDiagnostic(0, 0, null));
            if (s.Scope == 2 && !absent) diagnostics.Add(new CapabilityDiagnostic(11, 0, null));
            if (s.Discovery != 2) diagnostics.Add(new CapabilityDiagnostic(s.Discovery == 3 ? 2 : 1, 0, null));
            bool c7Unknown = C7Unknown(s);
            if (scopeOk) for (int i = 0; i < n; i++)
                {
                    int k = kinds[i]; if (k == 0) continue; var c = cs[i]; bool required = k == 1 && C7Required(s); int expected = RequiredProperties[k] | (required ? 32 : 0); int permitted = c7Unknown && k == 1 ? expected | 32 : expected;
                    if ((c.Properties & expected) != expected) diagnostics.Add(new CapabilityDiagnostic(5, k, i));
                    if ((c.Properties & ~permitted) != 0) diagnostics.Add(new CapabilityDiagnostic(6, k, i));
                    if (k == 1 && c7Unknown) diagnostics.Add(new CapabilityDiagnostic(12, k, i));
                    if (c.ReadState == 2) diagnostics.Add(new CapabilityDiagnostic(c.Reason == 2 ? 8 : 7, k, i));
                }
            uint machine = 0, target = 0, machineUnknown = 0, targetUnknown = 0;
            int Decode(int k, int range, out CapabilityRangeValue? value)
            {
                value = null;
                if (!scopeOk || presence[k] != 2) return 0;

                CapabilityCharacteristic characteristic = cs[first[k]];
                if (characteristic.ReadState == (int)CapabilityReadState.Failed) return 3;
                if (characteristic.ReadState != (int)CapabilityReadState.Success) return 0;

                byte[] bytes = characteristic.Bytes;
                if (range < 0)
                {
                    if (bytes.Length != 8) return 2;
                    machine = U32(bytes, 0);
                    target = U32(bytes, 4);
                    machineUnknown = machine & 0xfffe0000U;
                    targetUnknown = target & 0xfffe0000U;
                    return 1;
                }

                return DecodeRange(range, bytes, signedResistanceTenths, out value) ? 1 : 2;
            }

            CapabilityRangeValue? ignoredFeatureValue;
            int fd = Decode(1, -1, out ignoredFeatureValue);
            long?[] feature = { presence[1], fd, scopeOk && presence[1] == 2 ? (long?)first[1] : null, machine, target, machineUnknown, targetUnknown };
            if (fd == 2) diagnostics.Add(new CapabilityDiagnostic(9, 1, first[1]));
            var ranges = new List<CapabilityRangeInspection>();
            for (int r = 0; r < 5; r++)
            {
                int k = 9 + r;
                CapabilityRangeValue? value;
                int d = Decode(k, r, out value);
                if (d == 2) diagnostics.Add(new CapabilityDiagnostic(9, k, first[k]));
                ranges.Add(new CapabilityRangeInspection(presence[k], d, scopeOk && presence[k] == 2 ? (int?)first[k] : null, value));
            }
            if (scopeOk) { if (presence[1] == 1) diagnostics.Add(new CapabilityDiagnostic(4, 1, null)); if ((presence[14] == 2 || presence[14] == 3) && presence[15] == 1) diagnostics.Add(new CapabilityDiagnostic(4, 15, null)); if (fd == 1) { if ((target & 0x1ffff) != 0 && presence[14] == 1) diagnostics.Add(new CapabilityDiagnostic(4, 14, null)); for (int b = 0; b < 5; b++) if ((target & (1U << b)) != 0 && presence[9 + RangeForTarget[b]] == 1) diagnostics.Add(new CapabilityDiagnostic(10, 9 + RangeForTarget[b], null)); } }
            int Reasons(int k, int unavailable, int invalid) { if (presence[k] == 0) return unavailable; if (presence[k] != 2) return invalid; int p = cs[first[k]].Properties; if (k == 1 && c7Unknown) return 1024 | (((p & 2) == 0 || (p & ~(2 | 32)) != 0) ? invalid : 0); int expected = RequiredProperties[k] | (k == 1 && C7Required(s) ? 32 : 0); return p == expected ? 0 : invalid; }
            var operations = new List<CapabilityOperation>();
            for (int opcode = 0; opcode < 21; opcode++)
            {
                int bit = TargetForOpcode[opcode], declaration = 0, prerequisite = 2, why = 0;
                if (!scopeOk) { why = 1; if (absent) { declaration = 1; prerequisite = 0; } else if (s.Scope == 2) prerequisite = 3; operations.Add(new CapabilityOperation(opcode, bit, opcode == 18 || opcode == 19 ? 1 : 0, declaration, prerequisite, why)); continue; }
                if (bit == 255) declaration = presence[14] == 2 ? 2 : presence[14] == 1 ? 1 : 0; else if (fd == 1) declaration = (target & (1U << bit)) != 0 ? 2 : 1;
                if (declaration == 1) { operations.Add(new CapabilityOperation(opcode, bit, opcode == 18 || opcode == 19 ? 1 : 0, declaration, 0, 0)); continue; }
                if (s.Discovery != 2) why |= 2; why |= Reasons(1, 4, 8); if (bit != 255 && presence[1] == 2) why |= fd == 2 ? 8 : fd == 1 ? 0 : 4; why |= Reasons(14, 16, 32) | Reasons(15, 64, 128);
                if (bit != 255 && bit < 5 && declaration == 2) { int r = RangeForTarget[bit], k = 9 + r; why |= Reasons(k, 256, 512); if (presence[k] == 2) why |= ranges[r].Decode == 2 ? 512 : ranges[r].Decode == 1 ? 0 : 256; }
                prerequisite = (why & (8 | 32 | 128 | 512)) != 0 ? 3 : why == 0 ? 1 : 2; operations.Add(new CapabilityOperation(opcode, bit, opcode == 18 || opcode == 19 ? 1 : 0, declaration, prerequisite, why));
            }
            var observations = new List<CapabilityObservation>();
            for (int i = 0; i < n; i++)
            {
                CapabilityCharacteristic characteristic = cs[i];
                observations.Add(new CapabilityObservation(i, characteristic.Uuid, characteristic.Properties, kinds[i], characteristic.ReadState, characteristic.Reason, characteristic.Bytes));
            }
            return new CapabilityReport(s, presence, feature, ranges, operations, observations, diagnostics);
        }
        private static bool C7Required(CapabilitySnapshot s) { return s.C7 != null && s.C7.BondingSupported == true && s.C7.FeatureMayChangeOverLifetime == true; }
        private static bool C7Unknown(CapabilitySnapshot s) { return !(s.C7 != null && (s.C7.BondingSupported == false || s.C7.FeatureMayChangeOverLifetime == false || (s.C7.BondingSupported == true && s.C7.FeatureMayChangeOverLifetime == true))); }
        private static void Validate(CapabilityCharacteristic c) { if (c == null || c.Uuid == null || c.Uuid.Length != 32 || c.ReadState < 0 || c.ReadState > 2 || c.Reason < 0 || c.Reason > 5 || (c.ReadState != 2 && c.Reason != 0) || (c.ReadState != 1 && c.Bytes.Length != 0)) throw new ArgumentOutOfRangeException(nameof(c)); for (int i = 0; i < c.Uuid.Length; i++) if (!((c.Uuid[i] >= '0' && c.Uuid[i] <= '9') || (c.Uuid[i] >= 'a' && c.Uuid[i] <= 'f'))) throw new ArgumentException("UUID must be canonical lowercase hexadecimal.", nameof(c)); }
        private static int Kind(string uuid) { if (uuid.Substring(0, 4) != "0000" || uuid.Substring(8) != Base) return 0; int value = Convert.ToInt32(uuid.Substring(4, 4), 16); return value >= 0x2acc && value <= 0x2ada ? value - 0x2acc + 1 : 0; }
        private static uint U32(byte[] b, int o) { return (uint)(b[o] | b[o + 1] << 8 | b[o + 2] << 16 | b[o + 3] << 24); }
        private static short S16(byte[] b, int o) { return (short)(b[o] | b[o + 1] << 8); }
        private static ushort U16(byte[] b, int o) { return (ushort)(b[o] | b[o + 1] << 8); }
        private static bool DecodeRange(int kind, byte[] b, bool signedResistance, out CapabilityRangeValue? value)
        {
            value = null;
            int min, max, inc, div;
            if (kind == 2 && !signedResistance)
            {
                if (b.Length != 3) return false;
                min = b[0]; max = b[1]; inc = b[2]; div = 1;
            }
            else if (kind == 3)
            {
                if (b.Length != 3) return false;
                min = b[0]; max = b[1]; inc = b[2]; div = 1;
            }
            else
            {
                if (b.Length != 6) return false;
                if (kind == 0) { min = U16(b, 0); max = U16(b, 2); inc = U16(b, 4); div = 100; }
                else { min = S16(b, 0); max = S16(b, 2); inc = U16(b, 4); div = (kind == 1 || kind == 2) ? 10 : 1; }
            }

            if (inc == 0 || min > max) return false;
            value = new CapabilityRangeValue(kind, min, max, inc, div, kind);
            return true;
        }
    }
}
