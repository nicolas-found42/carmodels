
void FUN_0022c048(int param_1,int param_2,int param_3,int param_4)

{
  ulong uVar1;
  uint uVar2;
  uint uVar3;
  uint *puVar4;
  uint uVar5;
  uint uVar6;
  ulong *puVar7;
  ulong *puVar8;
  ulong *puVar9;
  ulong uVar10;
  int iVar11;
  ulong uVar12;
  uint uVar13;
  ulong uVar14;
  int iVar15;
  int iVar16;
  undefined8 uStack_410;
  
  iVar16 = 0;
  if (0 < param_2) {
    iVar15 = *(int *)(param_1 + 0xf8);
    while( true ) {
      uVar13 = 0;
      do {
        uVar2 = *(uint *)(iVar16 * 4 + iVar15);
        iVar11 = ((uVar13 & 8) << 1 | (int)(uVar13 & 0x10) >> 1 | uVar13 & 0xffffffe7) * 4;
        uVar5 = uVar13 * 4 + uVar2;
        uVar13 = uVar13 + 1;
        uVar3 = uVar5 + 3 & 3;
        uVar6 = uVar5 & 3;
        uVar3 = (*(int *)((uVar5 + 3) - uVar3) << (3 - uVar3) * 8 |
                uVar2 & 0xffffffffU >> (uVar3 + 1) * 8) & -1 << (4 - uVar6) * 8 |
                *(uint *)(uVar5 - uVar6) >> uVar6 * 8;
        uVar2 = (int)&uStack_410 + iVar11 + 3;
        uVar6 = uVar2 & 3;
        puVar4 = (uint *)(uVar2 - uVar6);
        *puVar4 = *puVar4 & -1 << (uVar6 + 1) * 8 | uVar3 >> (3 - uVar6) * 8;
        *(uint *)((int)&uStack_410 + iVar11) = uVar3;
      } while ((int)uVar13 < 0x100);
      puVar7 = *(ulong **)(iVar16 * 4 + iVar15);
      puVar8 = &uStack_410;
      puVar9 = &uStack_410;
      if (((uint)puVar7 & 7) == 0) {
        do {
          uVar14 = puVar9[1];
          uVar10 = puVar9[2];
          uVar12 = puVar9[3];
          *puVar7 = *puVar9;
          puVar7[1] = uVar14;
          puVar7[2] = uVar10;
          puVar7[3] = uVar12;
          puVar9 = puVar9 + 4;
          puVar7 = puVar7 + 4;
        } while (puVar9 != (ulong *)&stack0xfffffff0);
      }
      else {
        do {
          uVar10 = *puVar8;
          uVar12 = puVar8[1];
          uVar14 = puVar8[2];
          uVar1 = puVar8[3];
          uVar13 = (int)puVar7 + 7U & 7;
          puVar9 = (ulong *)(((int)puVar7 + 7U) - uVar13);
          *puVar9 = *puVar9 & -1L << (uVar13 + 1) * 8 | uVar10 >> (7 - uVar13) * 8;
          uVar13 = (uint)puVar7 & 7;
          *(ulong *)((int)puVar7 - uVar13) =
               uVar10 << uVar13 * 8 |
               *(ulong *)((int)puVar7 - uVar13) & 0xffffffffffffffffU >> (8 - uVar13) * 8;
          uVar13 = (int)puVar7 + 0xfU & 7;
          puVar9 = (ulong *)(((int)puVar7 + 0xfU) - uVar13);
          *puVar9 = *puVar9 & -1L << (uVar13 + 1) * 8 | uVar12 >> (7 - uVar13) * 8;
          uVar13 = (uint)(puVar7 + 1) & 7;
          puVar9 = (ulong *)((int)(puVar7 + 1) - uVar13);
          *puVar9 = uVar12 << uVar13 * 8 | *puVar9 & 0xffffffffffffffffU >> (8 - uVar13) * 8;
          uVar13 = (int)puVar7 + 0x17U & 7;
          puVar9 = (ulong *)(((int)puVar7 + 0x17U) - uVar13);
          *puVar9 = *puVar9 & -1L << (uVar13 + 1) * 8 | uVar14 >> (7 - uVar13) * 8;
          uVar13 = (uint)(puVar7 + 2) & 7;
          puVar9 = (ulong *)((int)(puVar7 + 2) - uVar13);
          *puVar9 = uVar14 << uVar13 * 8 | *puVar9 & 0xffffffffffffffffU >> (8 - uVar13) * 8;
          uVar13 = (int)puVar7 + 0x1fU & 7;
          puVar9 = (ulong *)(((int)puVar7 + 0x1fU) - uVar13);
          *puVar9 = *puVar9 & -1L << (uVar13 + 1) * 8 | uVar1 >> (7 - uVar13) * 8;
          uVar13 = (uint)(puVar7 + 3) & 7;
          puVar9 = (ulong *)((int)(puVar7 + 3) - uVar13);
          *puVar9 = uVar1 << uVar13 * 8 | *puVar9 & 0xffffffffffffffffU >> (8 - uVar13) * 8;
          puVar8 = puVar8 + 4;
          puVar7 = puVar7 + 4;
        } while (puVar8 != (ulong *)&stack0xfffffff0);
      }
      iVar16 = iVar16 + 1;
      if (param_2 <= iVar16) break;
      iVar15 = *(int *)(param_1 + 0xf8);
    }
  }
  param_2 = param_2 + param_3;
  param_4 = param_2 + param_4;
  if (param_2 < param_4) {
    iVar16 = *(int *)(param_1 + 0xf8);
    while( true ) {
      uVar13 = 0;
      do {
        uVar5 = ((uVar13 & 8) << 1 | (int)(uVar13 & 0x10) >> 1 | uVar13 & 0xffffffe7) * 4;
        uVar6 = uVar13 * 4 + *(int *)(param_2 * 4 + iVar16);
        uVar13 = uVar13 + 1;
        uVar2 = uVar6 + 3 & 3;
        uVar3 = uVar6 & 3;
        uVar3 = (*(int *)((uVar6 + 3) - uVar2) << (3 - uVar2) * 8 |
                uVar5 & 0xffffffffU >> (uVar2 + 1) * 8) & -1 << (4 - uVar3) * 8 |
                *(uint *)(uVar6 - uVar3) >> uVar3 * 8;
        uVar2 = (int)&uStack_410 + uVar5 + 3;
        uVar6 = uVar2 & 3;
        puVar4 = (uint *)(uVar2 - uVar6);
        *puVar4 = *puVar4 & -1 << (uVar6 + 1) * 8 | uVar3 >> (3 - uVar6) * 8;
        *(uint *)((int)&uStack_410 + uVar5) = uVar3;
      } while ((int)uVar13 < 0x100);
      puVar7 = *(ulong **)(param_2 * 4 + iVar16);
      puVar8 = &uStack_410;
      puVar9 = &uStack_410;
      if (((uint)puVar7 & 7) == 0) {
        do {
          uVar10 = puVar9[1];
          uVar12 = puVar9[2];
          uVar14 = puVar9[3];
          *puVar7 = *puVar9;
          puVar7[1] = uVar10;
          puVar7[2] = uVar12;
          puVar7[3] = uVar14;
          puVar9 = puVar9 + 4;
          puVar7 = puVar7 + 4;
        } while (puVar9 != (ulong *)&stack0xfffffff0);
      }
      else {
        do {
          uVar10 = *puVar8;
          uVar12 = puVar8[1];
          uVar14 = puVar8[2];
          uVar1 = puVar8[3];
          uVar13 = (int)puVar7 + 7U & 7;
          puVar9 = (ulong *)(((int)puVar7 + 7U) - uVar13);
          *puVar9 = *puVar9 & -1L << (uVar13 + 1) * 8 | uVar10 >> (7 - uVar13) * 8;
          uVar13 = (uint)puVar7 & 7;
          *(ulong *)((int)puVar7 - uVar13) =
               uVar10 << uVar13 * 8 |
               *(ulong *)((int)puVar7 - uVar13) & 0xffffffffffffffffU >> (8 - uVar13) * 8;
          uVar13 = (int)puVar7 + 0xfU & 7;
          puVar9 = (ulong *)(((int)puVar7 + 0xfU) - uVar13);
          *puVar9 = *puVar9 & -1L << (uVar13 + 1) * 8 | uVar12 >> (7 - uVar13) * 8;
          uVar13 = (uint)(puVar7 + 1) & 7;
          puVar9 = (ulong *)((int)(puVar7 + 1) - uVar13);
          *puVar9 = uVar12 << uVar13 * 8 | *puVar9 & 0xffffffffffffffffU >> (8 - uVar13) * 8;
          uVar13 = (int)puVar7 + 0x17U & 7;
          puVar9 = (ulong *)(((int)puVar7 + 0x17U) - uVar13);
          *puVar9 = *puVar9 & -1L << (uVar13 + 1) * 8 | uVar14 >> (7 - uVar13) * 8;
          uVar13 = (uint)(puVar7 + 2) & 7;
          puVar9 = (ulong *)((int)(puVar7 + 2) - uVar13);
          *puVar9 = uVar14 << uVar13 * 8 | *puVar9 & 0xffffffffffffffffU >> (8 - uVar13) * 8;
          uVar13 = (int)puVar7 + 0x1fU & 7;
          puVar9 = (ulong *)(((int)puVar7 + 0x1fU) - uVar13);
          *puVar9 = *puVar9 & -1L << (uVar13 + 1) * 8 | uVar1 >> (7 - uVar13) * 8;
          uVar13 = (uint)(puVar7 + 3) & 7;
          puVar9 = (ulong *)((int)(puVar7 + 3) - uVar13);
          *puVar9 = uVar1 << uVar13 * 8 | *puVar9 & 0xffffffffffffffffU >> (8 - uVar13) * 8;
          puVar8 = puVar8 + 4;
          puVar7 = puVar7 + 4;
        } while (puVar8 != (ulong *)&stack0xfffffff0);
      }
      param_2 = param_2 + 1;
      if (param_4 <= param_2) break;
      iVar16 = *(int *)(param_1 + 0xf8);
    }
  }
  return;
}

