
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../fr2/source/database/db_setup.c:765 */

void FUN_001da270(undefined8 param_1,int param_2,ulong param_3,ulong param_4)

{
  byte bVar1;
  uint uVar2;
  uint uVar3;
  undefined4 uVar4;
  ulong *puVar5;
  ulong uVar6;
  long lVar7;
  long lVar8;
  ulong in_v1;
  ulong uVar9;
  ulong uVar10;
  ulong uVar11;
  int iVar12;
  float fVar13;
  float fVar14;
  float afStack_40 [4];
  
  iVar12 = (int)param_1;
  *(undefined4 *)(iVar12 + 0x18) = *(undefined4 *)(param_2 + 0x18);
  bVar1 = *(byte *)(param_2 + 0x14);
  *(byte *)(iVar12 + 0x14) = bVar1;
  uVar2 = param_2 + 0x23U & 7;
  uVar3 = param_2 + 0x1cU & 7;
  uVar6 = (*(long *)((param_2 + 0x23U) - uVar2) << (7 - uVar2) * 8 |
          (ulong)bVar1 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0x1cU) - uVar3) >> uVar3 * 8;
  uVar2 = param_2 + 0x2bU & 7;
  uVar3 = param_2 + 0x24U & 7;
  uVar9 = (*(long *)((param_2 + 0x2bU) - uVar2) << (7 - uVar2) * 8 |
          in_v1 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0x24U) - uVar3) >> uVar3 * 8;
  uVar2 = param_2 + 0x33U & 7;
  uVar3 = param_2 + 0x2cU & 7;
  uVar10 = (*(long *)((param_2 + 0x33U) - uVar2) << (7 - uVar2) * 8 |
           param_3 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
           *(ulong *)((param_2 + 0x2cU) - uVar3) >> uVar3 * 8;
  uVar2 = param_2 + 0x3bU & 7;
  uVar3 = param_2 + 0x34U & 7;
  uVar11 = (*(long *)((param_2 + 0x3bU) - uVar2) << (7 - uVar2) * 8 |
           param_4 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
           *(ulong *)((param_2 + 0x34U) - uVar3) >> uVar3 * 8;
  uVar2 = iVar12 + 0x23U & 7;
  puVar5 = (ulong *)((iVar12 + 0x23U) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x1cU & 7;
  puVar5 = (ulong *)((iVar12 + 0x1cU) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  uVar2 = iVar12 + 0x2bU & 7;
  puVar5 = (ulong *)((iVar12 + 0x2bU) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar9 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x24U & 7;
  puVar5 = (ulong *)((iVar12 + 0x24U) - uVar2);
  *puVar5 = uVar9 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  uVar2 = iVar12 + 0x33U & 7;
  puVar5 = (ulong *)((iVar12 + 0x33U) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar10 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x2cU & 7;
  puVar5 = (ulong *)((iVar12 + 0x2cU) - uVar2);
  *puVar5 = uVar10 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  uVar2 = iVar12 + 0x3bU & 7;
  puVar5 = (ulong *)((iVar12 + 0x3bU) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar11 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x34U & 7;
  puVar5 = (ulong *)((iVar12 + 0x34U) - uVar2);
  *puVar5 = uVar11 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  uVar2 = param_2 + 0x43U & 7;
  uVar3 = param_2 + 0x3cU & 7;
  uVar6 = (*(long *)((param_2 + 0x43U) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0x3cU) - uVar3) >> uVar3 * 8;
  uVar2 = iVar12 + 0x43U & 7;
  puVar5 = (ulong *)((iVar12 + 0x43U) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x3cU & 7;
  puVar5 = (ulong *)((iVar12 + 0x3cU) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  uVar2 = param_2 + 0x4bU & 7;
  uVar3 = param_2 + 0x44U & 7;
  uVar6 = (*(long *)((param_2 + 0x4bU) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0x44U) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0x4c);
  uVar2 = iVar12 + 0x4bU & 7;
  puVar5 = (ulong *)((iVar12 + 0x4bU) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x44U & 7;
  puVar5 = (ulong *)((iVar12 + 0x44U) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0x4c) = uVar4;
  *(undefined4 *)(iVar12 + 0x50) = *(undefined4 *)(param_2 + 0x50);
  uVar2 = param_2 + 0x5bU & 7;
  uVar3 = param_2 + 0x54U & 7;
  uVar6 = (*(long *)((param_2 + 0x5bU) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0x54U) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0x5c);
  uVar2 = iVar12 + 0x5bU & 7;
  puVar5 = (ulong *)((iVar12 + 0x5bU) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x54U & 7;
  puVar5 = (ulong *)((iVar12 + 0x54U) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0x5c) = uVar4;
  uVar6 = *(ulong *)(param_2 + 0x60);
  *(ulong *)(iVar12 + 0x60) = uVar6;
  *(undefined4 *)(iVar12 + 0x68) = *(undefined4 *)(param_2 + 0x68);
  uVar2 = param_2 + 0x73U & 7;
  uVar3 = param_2 + 0x6cU & 7;
  uVar6 = (*(long *)((param_2 + 0x73U) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0x6cU) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0x74);
  uVar2 = iVar12 + 0x73U & 7;
  puVar5 = (ulong *)((iVar12 + 0x73U) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x6cU & 7;
  puVar5 = (ulong *)((iVar12 + 0x6cU) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0x74) = uVar4;
  uVar6 = *(ulong *)(param_2 + 0x78);
  *(ulong *)(iVar12 + 0x78) = uVar6;
  *(undefined4 *)(iVar12 + 0x80) = *(undefined4 *)(param_2 + 0x80);
  uVar2 = param_2 + 0x8bU & 7;
  uVar3 = param_2 + 0x84U & 7;
  uVar6 = (*(long *)((param_2 + 0x8bU) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0x84U) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0x8c);
  uVar2 = iVar12 + 0x8bU & 7;
  puVar5 = (ulong *)((iVar12 + 0x8bU) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x84U & 7;
  puVar5 = (ulong *)((iVar12 + 0x84U) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0x8c) = uVar4;
  uVar6 = *(ulong *)(param_2 + 0x90);
  *(ulong *)(iVar12 + 0x90) = uVar6;
  *(undefined4 *)(iVar12 + 0x98) = *(undefined4 *)(param_2 + 0x98);
  uVar2 = param_2 + 0xa3U & 7;
  uVar3 = param_2 + 0x9cU & 7;
  uVar6 = (*(long *)((param_2 + 0xa3U) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0x9cU) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0xa4);
  uVar2 = iVar12 + 0xa3U & 7;
  puVar5 = (ulong *)((iVar12 + 0xa3U) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0x9cU & 7;
  puVar5 = (ulong *)((iVar12 + 0x9cU) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0xa4) = uVar4;
  uVar6 = *(ulong *)(param_2 + 0xa8);
  *(ulong *)(iVar12 + 0xa8) = uVar6;
  *(undefined4 *)(iVar12 + 0xb0) = *(undefined4 *)(param_2 + 0xb0);
  uVar2 = param_2 + 0xbbU & 7;
  uVar3 = param_2 + 0xb4U & 7;
  uVar6 = (*(long *)((param_2 + 0xbbU) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0xb4U) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0xbc);
  uVar2 = iVar12 + 0xbbU & 7;
  puVar5 = (ulong *)((iVar12 + 0xbbU) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0xb4U & 7;
  puVar5 = (ulong *)((iVar12 + 0xb4U) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0xbc) = uVar4;
  uVar6 = *(ulong *)(param_2 + 0xc0);
  *(ulong *)(iVar12 + 0xc0) = uVar6;
  *(undefined4 *)(iVar12 + 200) = *(undefined4 *)(param_2 + 200);
  uVar2 = param_2 + 0xd3U & 7;
  uVar3 = param_2 + 0xccU & 7;
  uVar6 = (*(long *)((param_2 + 0xd3U) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0xccU) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0xd4);
  uVar2 = iVar12 + 0xd3U & 7;
  puVar5 = (ulong *)((iVar12 + 0xd3U) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0xccU & 7;
  puVar5 = (ulong *)((iVar12 + 0xccU) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0xd4) = uVar4;
  uVar6 = *(ulong *)(param_2 + 0xd8);
  *(ulong *)(iVar12 + 0xd8) = uVar6;
  *(undefined4 *)(iVar12 + 0xe0) = *(undefined4 *)(param_2 + 0xe0);
  uVar2 = param_2 + 0xebU & 7;
  uVar3 = param_2 + 0xe4U & 7;
  uVar6 = (*(long *)((param_2 + 0xebU) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0xe4U) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0xec);
  uVar2 = iVar12 + 0xebU & 7;
  puVar5 = (ulong *)((iVar12 + 0xebU) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0xe4U & 7;
  puVar5 = (ulong *)((iVar12 + 0xe4U) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0xec) = uVar4;
  *(undefined8 *)(iVar12 + 0xf0) = *(undefined8 *)(param_2 + 0xf0);
  *(undefined4 *)(iVar12 + 0xf8) = *(undefined4 *)(param_2 + 0xf8);
  uVar6 = *(ulong *)(param_2 + 0x108);
  *(ulong *)(iVar12 + 0x108) = uVar6;
  *(undefined4 *)(iVar12 + 0x110) = *(undefined4 *)(param_2 + 0x110);
  uVar2 = param_2 + 0x103U & 7;
  uVar3 = param_2 + 0xfcU & 7;
  uVar6 = (*(long *)((param_2 + 0x103U) - uVar2) << (7 - uVar2) * 8 |
          uVar6 & 0xffffffffffffffffU >> (uVar2 + 1) * 8) & -1L << (8 - uVar3) * 8 |
          *(ulong *)((param_2 + 0xfcU) - uVar3) >> uVar3 * 8;
  uVar4 = *(undefined4 *)(param_2 + 0x104);
  uVar2 = iVar12 + 0x103U & 7;
  puVar5 = (ulong *)((iVar12 + 0x103U) - uVar2);
  *puVar5 = *puVar5 & -1L << (uVar2 + 1) * 8 | uVar6 >> (7 - uVar2) * 8;
  uVar2 = iVar12 + 0xfcU & 7;
  puVar5 = (ulong *)((iVar12 + 0xfcU) - uVar2);
  *puVar5 = uVar6 << uVar2 * 8 | *puVar5 & 0xffffffffffffffffU >> (8 - uVar2) * 8;
  *(undefined4 *)(iVar12 + 0x104) = uVar4;
  *(undefined8 *)(iVar12 + 0x120) = *(undefined8 *)(param_2 + 0x120);
  *(undefined8 *)(iVar12 + 0x128) = *(undefined8 *)(param_2 + 0x128);
  *(undefined8 *)(iVar12 + 0x130) = *(undefined8 *)(param_2 + 0x130);
  *(undefined8 *)(iVar12 + 0x138) = *(undefined8 *)(param_2 + 0x138);
  *(undefined8 *)(iVar12 + 0x140) = *(undefined8 *)(param_2 + 0x140);
  *(undefined8 *)(iVar12 + 0x148) = *(undefined8 *)(param_2 + 0x148);
  lVar7 = FUN_001d5f90();
  if (lVar7 == 0) {
                    /* WARNING: Subroutine does not return */
    FUN_00105888(0x289b48,0x2fd,0x289c80,param_1);
  }
  fVar14 = 57.295776;
  FUN_001ca0f0(lVar7,1,afStack_40);
  fVar13 = *(float *)(iVar12 + 0x58);
  afStack_40[0] = afStack_40[0] * fVar14;
  if (1.0 < ABS(afStack_40[0] - fVar13)) {
    FUN_001b9508(0x289ba0,lVar7);
    fVar13 = *(float *)(iVar12 + 0x58);
  }
  lVar8 = FUN_001c9908(fVar13 * 0.01745329,lVar7,1);
  if (lVar8 == 0) {
    FUN_001b9508(0x289be8,PTR_s_FRONT_SPOILER_0023a9fc);
  }
  FUN_001ca0f0(lVar7,8,afStack_40);
  fVar13 = *(float *)(iVar12 + 0x5c);
  afStack_40[0] = afStack_40[0] * fVar14;
  if (1.0 < ABS(afStack_40[0] - fVar13)) {
    FUN_001b9508(0x289c10,lVar7);
    fVar13 = *(float *)(iVar12 + 0x5c);
  }
  lVar7 = FUN_001c9908(fVar13 * 0.01745329,lVar7,8);
  if (lVar7 == 0) {
    FUN_001b9508(0x289be8,PTR_s_REAR_SPOILER_0023aa18);
  }
  return;
}

