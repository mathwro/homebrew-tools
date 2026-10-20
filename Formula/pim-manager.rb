class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.3.0/pim-manager_0.3.0_darwin_arm64.tar.gz"
      sha256 "747599e35da63a7eb1d7e85ed3c49490bafe934be3f722773eff28c26f6068c1"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.3.0/pim-manager_0.3.0_darwin_amd64.tar.gz"
      sha256 "b73aba8f5a48824fd7872324f77fedc0ffbbd4705068be9b76ddef9e1d2f008b"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.3.0/pim-manager_0.3.0_linux_arm64.tar.gz"
      sha256 "2b09845534e8ee600174cb9984fd235ec444b37a92816fe5ddf0814fd811f722"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.3.0/pim-manager_0.3.0_linux_amd64.tar.gz"
      sha256 "65f705f0e39aa9c919a97790b4b8ecbbcdbaffbfa1d4202990e37507c868ccd1"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
