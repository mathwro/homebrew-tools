class Azc < Formula
  desc "Fast subscription context switcher for Azure CLI"
  homepage "https://github.com/mathwro/azc"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.6.0/azc_0.6.0_darwin_arm64.tar.gz"
      sha256 "468ae8ef1bea9691b48d5dcbe310c29a9a99b02d793fa31d957173a7fb79f426"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.6.0/azc_0.6.0_darwin_amd64.tar.gz"
      sha256 "ac8874f2f72f72c2bc32b8d4f7cc748440bb26e27fd0601ffafdbd7f1829b3be"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.6.0/azc_0.6.0_linux_arm64.tar.gz"
      sha256 "9738f84c321c0bc6268bf61b9433f304d368c053379ab27f3161024d92c45aba"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.6.0/azc_0.6.0_linux_amd64.tar.gz"
      sha256 "dd551898363848320f55c6f3d081da864c4d625fbce6a805a7d6ebed7266fd1c"
    end
  end

  def install
    bin.install "azc"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/azc --version")
  end
end
