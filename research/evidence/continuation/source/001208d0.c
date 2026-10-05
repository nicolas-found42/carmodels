
uint * FUN_001208d0(uint *param_1,uint param_2,undefined8 param_3)

{
  undefined2 *puVar1;
  uint *puVar2;
  uint uVar3;
  uint uVar4;
  undefined2 *puVar5;
  uint *puVar6;
  uint uVar7;
  uint *puVar8;
  uint uVar9;
  uint uVar10;
  
  uVar10 = *param_1;
  puVar8 = (uint *)param_3;
  uVar7 = puVar8[1];
  uVar4 = (param_1[1] & 1) << 0xf;
  uVar3 = (param_1[1] >> 1 & 1) << 0x18;
  puVar8[1] = uVar7 & 0xfeff7fff | uVar4 | uVar3;
  puVar8[3] = param_1[2];
  uVar9 = param_1[3];
  *puVar8 = uGpffff93b4 & 0xfff00000 | 0x30000 | uVar10 & 0xffff;
  puVar8[4] = uVar9;
  puVar8[9] = param_2;
  uVar10 = param_1[4];
  puVar8[2] = 0;
  puVar8[5] = uVar10;
  puVar8[6] = param_1[5];
  puVar8[7] = param_1[6];
  puVar6 = param_1 + 9;
  uVar10 = param_1[8];
  puVar8[8] = param_1[7];
  puVar8[1] = uVar7 & 0xfeff40ff | uVar4 | uVar3 | (uVar10 & 0x3f) << 8;
  if (uVar10 != 0) {
    uVar10 = uVar10 & 0x3f;
    puVar8[2] = (uint)puGpffffaa14;
    puVar1 = puGpffffaa14 + uVar10 * 2;
    puVar5 = puGpffffaa14;
    for (; puGpffffaa14 = puVar1, uVar10 != 0; uVar10 = uVar10 - 1) {
      uVar7 = puVar6[1];
      *puVar5 = (short)*puVar6;
      puVar5[1] = (short)uVar7;
      puVar5 = puVar5 + 2;
      puVar6 = puVar6 + 2;
    }
  }
  puVar2 = puVar6 + 1;
  puVar8[10] = 0;
  uVar10 = *puVar6;
  *(char *)(puVar8 + 1) = (char)uVar10;
  if (uVar10 != 0) {
    uVar10 = uVar10 & 0xff;
    puVar8[10] = uGpffffaa18;
    uVar3 = uGpffffaa18 + uVar10 * 0x2c;
    uVar7 = uGpffffaa18;
    for (; uGpffffaa18 = uVar3, uVar10 != 0; uVar10 = uVar10 - 1) {
      puVar2 = (uint *)FUN_001208d0(puVar2,param_3,uVar7);
      uVar7 = uVar7 + 0x2c;
      uVar3 = uGpffffaa18;
    }
  }
  return puVar2;
}

