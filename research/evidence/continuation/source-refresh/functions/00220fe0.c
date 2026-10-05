
void FUN_00220fe0(long param_1,undefined8 param_2)

{
  byte bVar1;
  undefined4 *puVar2;
  uint uVar3;
  long lVar4;
  undefined1 uVar5;
  undefined1 uVar6;
  int *piVar7;
  undefined2 uStack_40;
  undefined2 auStack_3e [7];
  
  if (param_1 == 0) {
    return;
  }
  lVar4 = FUN_001106d8();
  piVar7 = (int *)param_1;
  if (lVar4 == 0) {
    uRam0028ef58 = 0x50;
    FUN_0010aec0(&DAT_002b7480 + iRam0028ef54 * 0x10,*(undefined4 *)(iRam0028ef54 * 4 + 0x2906e8),0)
    ;
    puRam002906f0 = &DAT_002b7480 + iRam0028ef54 * 0x10;
    uRam0028ef5c = 0;
    lVar4 = FUN_002209d8(param_2,param_1,&uStack_40);
    if (lVar4 != 0) {
      do {
        uVar3 = REG_DMAC_2_GIF_CHCR;
      } while ((uVar3 & 0x100) != 0);
      lVar4 = *(long *)(piVar7 + 0xe);
      if (((lVar4 << 0x18) >> 0x20 & 1U) == 0) {
        uVar5 = (&DAT_00232d99)[(uint)*(byte *)(piVar7 + 0xd) * 0xf];
        uVar6 = (&DAT_00232d92)[(uint)*(byte *)(piVar7 + 0xd) * 0xf];
      }
      else {
        uVar5 = 0;
        uVar6 = 0x20;
      }
      FUN_00222110(puRam002906f0,piVar7[10],uStack_40,*(ulong *)(piVar7 + 0xc) >> 0x16 & 0x3f,uVar5,
                   uVar6,1 << ((uint)((ulong)(lVar4 << 9) >> 0x20) & 0xf),
                   1 << ((uint)((ulong)(lVar4 << 5) >> 0x20) & 0xf));
    }
    if ((&DAT_00232d91)[(uint)*(byte *)(piVar7 + 0xd) * 0xf] == '\0') {
      auStack_3e[0] = 0;
    }
    else {
      puVar2 = (undefined4 *)*piVar7;
      lVar4 = FUN_00220b90(4,puVar2,auStack_3e);
      if (lVar4 != 0) {
        if (puVar2[1] == 1) {
          FUN_00222110(puRam002906f0,*puVar2,auStack_3e[0],1,0,0x20,8,2);
        }
        else {
          FUN_00222110(puRam002906f0,*puVar2,auStack_3e[0],1,0,0x20,0x10,0x10);
        }
      }
    }
    FUN_00222260();
  }
  else {
    uRam0028ef58 = 0x50;
    puRam002906f0 = puRam0028eeb8;
    lVar4 = FUN_002209d8(param_2,param_1,&uStack_40);
    if (lVar4 == 0) {
      bVar1 = *(byte *)(piVar7 + 0xd);
    }
    else {
      lVar4 = *(long *)(piVar7 + 0xe);
      if (((lVar4 << 0x18) >> 0x20 & 1U) == 0) {
        uVar5 = (&DAT_00232d99)[(uint)*(byte *)(piVar7 + 0xd) * 0xf];
        uVar6 = (&DAT_00232d92)[(uint)*(byte *)(piVar7 + 0xd) * 0xf];
      }
      else {
        uVar5 = 0;
        uVar6 = 0x20;
      }
      FUN_00222110(puRam002906f0,piVar7[10],uStack_40,*(ulong *)(piVar7 + 0xc) >> 0x16 & 0x3f,uVar5,
                   uVar6,1 << ((uint)((ulong)(lVar4 << 9) >> 0x20) & 0xf),
                   1 << ((uint)((ulong)(lVar4 << 5) >> 0x20) & 0xf));
      bVar1 = *(byte *)(piVar7 + 0xd);
    }
    if ((&DAT_00232d91)[(uint)bVar1 * 0xf] == '\0') {
      auStack_3e[0] = 0;
    }
    else {
      puVar2 = (undefined4 *)*piVar7;
      lVar4 = FUN_00220b90(4,puVar2,auStack_3e);
      if (lVar4 != 0) {
        if (puVar2[1] == 1) {
          FUN_00222110(puRam002906f0,*puVar2,auStack_3e[0],1,0,0x20,8,2);
          uRam0028ef5c = 0;
        }
        else {
          FUN_00222110(puRam002906f0,*puVar2,auStack_3e[0],1,0,0x20,0x10,0x10);
          uRam0028ef5c = 0;
        }
        goto LAB_0022135c;
      }
    }
    uRam0028ef5c = 0;
  }
LAB_0022135c:
  FUN_00220d60(param_1,uStack_40,auStack_3e[0]);
  return;
}

